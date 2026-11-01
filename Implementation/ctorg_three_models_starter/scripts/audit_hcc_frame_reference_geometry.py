from pathlib import Path
import numpy as np
import pandas as pd
import pydicom

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
audit = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit")
link_file = audit / "hcc_ct_seg_linkage_new_download.csv"
out_frames = audit / "hcc_seg_frame_reference_geometry.csv"
out_cases = audit / "hcc_seg_frame_reference_geometry_summary.csv"

links = pd.read_csv(link_file, dtype=str).fillna("")
ct = {}

print("Indexing CT instances...")
for p in root.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(
            str(p), stop_before_pixels=True, force=True,
            specific_tags=[
                "Modality", "SOPInstanceUID", "SeriesInstanceUID",
                "PatientID", "FrameOfReferenceUID",
                "ImagePositionPatient", "ImageOrientationPatient",
                "PixelSpacing"
            ]
        )
        if str(getattr(d, "Modality", "")).upper() != "CT":
            continue
        uid = str(getattr(d, "SOPInstanceUID", ""))
        if not uid:
            continue
        ct[uid] = {
            "path": str(p),
            "patient": str(getattr(d, "PatientID", "")),
            "series": str(getattr(d, "SeriesInstanceUID", "")),
            "for_uid": str(getattr(d, "FrameOfReferenceUID", "")),
            "pos": np.asarray(getattr(d, "ImagePositionPatient", []), dtype=float),
            "ori": np.asarray(getattr(d, "ImageOrientationPatient", []), dtype=float),
            "spacing": np.asarray(getattr(d, "PixelSpacing", []), dtype=float),
        }
    except Exception:
        pass

print("CT instances indexed:", len(ct))

def first_seq_value(group, seq_name, field):
    seq = getattr(group, seq_name, []) if group else []
    if seq and hasattr(seq[0], field):
        return np.asarray([float(v) for v in getattr(seq[0], field)])
    return None

frame_rows = []

for _, link in links.iterrows():
    patient = link.get("PatientID", "")
    seg_path = Path(link.get("SEG_path", ""))
    if not seg_path.exists():
        continue

    try:
        ds = pydicom.dcmread(str(seg_path), force=True)
        shared = getattr(ds, "SharedFunctionalGroupsSequence", [])
        shared0 = shared[0] if shared else None
        seg_ori = first_seq_value(shared0, "PlaneOrientationSequence",
                                  "ImageOrientationPatient")
        seg_spacing = first_seq_value(shared0, "PixelMeasuresSequence",
                                      "PixelSpacing")
        seg_for = str(getattr(ds, "FrameOfReferenceUID", ""))

        for frame_no, frame in enumerate(
            getattr(ds, "PerFrameFunctionalGroupsSequence", []), start=1
        ):
            pos = first_seq_value(frame, "PlanePositionSequence",
                                  "ImagePositionPatient")
            seg_num = ""
            segment_ids = getattr(frame, "SegmentIdentificationSequence", [])
            if segment_ids:
                seg_num = str(getattr(segment_ids[0], "ReferencedSegmentNumber", ""))

            source_uids = []
            for deriv in getattr(frame, "DerivationImageSequence", []):
                for src in getattr(deriv, "SourceImageSequence", []):
                    uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
                    if uid:
                        source_uids.append(uid)

            if not source_uids:
                frame_rows.append({
                    "PatientID": patient, "frame": frame_no,
                    "segment_number": seg_num, "reference_uid": "",
                    "frame_status": "NO_FRAME_LEVEL_SOURCE_REFERENCE"
                })
                continue

            for uid in source_uids:
                row = {
                    "PatientID": patient, "frame": frame_no,
                    "segment_number": seg_num, "reference_uid": uid,
                    "SEG_FrameOfReferenceUID": seg_for,
                    "frame_status": "",
                }
                target = ct.get(uid)

                if target is None:
                    row["frame_status"] = "REFERENCED_CT_NOT_FOUND_LOCALLY"
                    frame_rows.append(row)
                    continue

                row["CT_patient"] = target["patient"]
                row["CT_series"] = target["series"]
                row["patient_match"] = target["patient"] == patient
                row["frame_of_reference_match"] = (
                    bool(seg_for) and seg_for == target["for_uid"]
                )

                if seg_ori is not None and len(seg_ori) == 6 and len(target["ori"]) == 6:
                    row["orientation_match"] = bool(
                        np.allclose(seg_ori, target["ori"], atol=1e-4)
                    )
                else:
                    row["orientation_match"] = ""

                if seg_spacing is not None and len(seg_spacing) == 2 and len(target["spacing"]) == 2:
                    row["pixel_spacing_match"] = bool(
                        np.allclose(seg_spacing, target["spacing"], atol=1e-4)
                    )
                else:
                    row["pixel_spacing_match"] = ""

                if pos is not None and len(pos) == 3 and len(target["pos"]) == 3:
                    delta = pos - target["pos"]
                    row["position_delta_mm"] = float(np.linalg.norm(delta))

                    if len(target["ori"]) == 6:
                        row_dir = target["ori"][:3]
                        col_dir = target["ori"][3:]
                        normal = np.cross(row_dir, col_dir)
                        row["in_plane_delta_mm"] = float(np.hypot(
                            np.dot(delta, row_dir), np.dot(delta, col_dir)
                        ))
                        row["normal_delta_mm"] = float(abs(np.dot(delta, normal)))
                    else:
                        row["in_plane_delta_mm"] = np.nan
                        row["normal_delta_mm"] = np.nan
                else:
                    row["position_delta_mm"] = np.nan
                    row["in_plane_delta_mm"] = np.nan
                    row["normal_delta_mm"] = np.nan

                row["frame_status"] = "REFERENCE_FOUND"
                frame_rows.append(row)

    except Exception as exc:
        frame_rows.append({
            "PatientID": patient, "reference_uid": "",
            "frame_status": "SEG_READ_ERROR", "error": repr(exc)
        })

frames = pd.DataFrame(frame_rows)
frames.to_csv(out_frames, index=False)

summary_rows = []
for patient, group in frames.groupby("PatientID"):
    found = group[group["frame_status"] == "REFERENCE_FOUND"]
    summary_rows.append({
        "PatientID": patient,
        "SEG_frames_or_reference_rows": len(group),
        "resolved_frame_reference_rows": len(found),
        "unique_referenced_CT_instances": found["reference_uid"].nunique(),
        "patient_matches_all": (
            bool(found["patient_match"].eq(True).all()) if len(found) else ""
        ),
        "frame_of_reference_matches_all": (
            bool(found["frame_of_reference_match"].eq(True).all()) if len(found) else ""
        ),
        "orientation_matches_all": (
            bool(found["orientation_match"].eq(True).all()) if len(found) else ""
        ),
        "pixel_spacing_matches_all": (
            bool(found["pixel_spacing_match"].eq(True).all()) if len(found) else ""
        ),
        "max_in_plane_delta_mm": (
            found["in_plane_delta_mm"].max() if len(found) else np.nan
        ),
        "max_normal_delta_mm": (
            found["normal_delta_mm"].max() if len(found) else np.nan
        ),
        "median_normal_delta_mm": (
            found["normal_delta_mm"].median() if len(found) else np.nan
        ),
        "max_total_position_delta_mm": (
            found["position_delta_mm"].max() if len(found) else np.nan
        ),
        "reference_rows_without_local_CT": int(
            group["frame_status"].eq("REFERENCED_CT_NOT_FOUND_LOCALLY").sum()
        ),
        "frames_without_source_reference": int(
            group["frame_status"].eq("NO_FRAME_LEVEL_SOURCE_REFERENCE").sum()
        ),
    })

summary = pd.DataFrame(summary_rows)
summary.to_csv(out_cases, index=False)

print("\n=== FRAME-LEVEL STATUS ===")
print(frames["frame_status"].value_counts().to_string())

print("\n=== REVIEW CASE SUMMARY ===")
review_ids = [
    "HCC_003", "HCC_012", "HCC_015", "HCC_016", "HCC_019",
    "HCC_024", "HCC_028", "HCC_043", "HCC_048", "HCC_068",
    "HCC_089", "HCC_091", "HCC_094", "HCC_097", "HCC_099",
    "HCC_101", "HCC_103"
]
cols = [
    "PatientID", "resolved_frame_reference_rows",
    "unique_referenced_CT_instances", "patient_matches_all",
    "frame_of_reference_matches_all", "orientation_matches_all",
    "pixel_spacing_matches_all", "max_in_plane_delta_mm",
    "max_normal_delta_mm", "median_normal_delta_mm",
    "max_total_position_delta_mm", "frames_without_source_reference"
]
print(summary[summary["PatientID"].isin(review_ids)][cols].to_string(index=False))

print("\nSaved frame report:", out_frames)
print("Saved patient summary:", out_cases)
