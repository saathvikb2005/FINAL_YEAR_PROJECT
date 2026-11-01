from pathlib import Path
import numpy as np
import pandas as pd
import pydicom

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
audit = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit")
link_file = audit / "hcc_ct_seg_linkage_new_download.csv"
out_file = audit / "hcc_ct_seg_geometry_alignment.csv"

links = pd.read_csv(link_file, dtype=str).fillna("")
rows = []

def vals(obj, sequence_name, field):
    seq = getattr(obj, sequence_name, []) if obj else []
    if seq and hasattr(seq[0], field):
        return np.asarray([float(x) for x in getattr(seq[0], field)])
    return None

# Index local CT instances by SOP Instance UID.
ct_index = {}
for p in root.rglob("*.dcm"):
    try:
        h = pydicom.dcmread(
            str(p), stop_before_pixels=True, force=True,
            specific_tags=[
                "Modality", "SOPInstanceUID", "SeriesInstanceUID",
                "PatientID", "FrameOfReferenceUID",
                "ImagePositionPatient", "ImageOrientationPatient",
                "PixelSpacing"
            ]
        )
        if str(getattr(h, "Modality", "")).upper() != "CT":
            continue
        sop = str(getattr(h, "SOPInstanceUID", ""))
        if sop:
            ct_index[sop] = {
                "path": p,
                "series": str(getattr(h, "SeriesInstanceUID", "")),
                "patient": str(getattr(h, "PatientID", "")),
                "for_uid": str(getattr(h, "FrameOfReferenceUID", "")),
                "ipp": np.asarray(getattr(h, "ImagePositionPatient", []), dtype=float),
                "iop": np.asarray(getattr(h, "ImageOrientationPatient", []), dtype=float),
                "spacing": np.asarray(getattr(h, "PixelSpacing", []), dtype=float),
            }
    except Exception:
        pass

print("Indexed CT SOP instances:", len(ct_index))

for _, link in links.iterrows():
    patient = link.get("PatientID", "")
    seg_path = Path(link.get("SEG_path", ""))
    status = link.get("link_status", "")
    resolved_series = link.get("resolved_local_CT_series", "")

    result = {
        "PatientID": patient,
        "link_status": status,
        "resolved_CT_series": resolved_series,
        "SEG_path": str(seg_path),
        "SEG_FrameOfReferenceUID": "",
        "CT_FrameOfReferenceUID": "",
        "SEG_frames": 0,
        "frames_with_source_CT_reference": 0,
        "source_refs_found_locally": 0,
        "same_patient": "",
        "same_series": "",
        "frame_of_reference_match": "",
        "orientation_match": "",
        "pixel_spacing_match": "",
        "position_match_within_0.1mm": "",
        "max_position_delta_mm": np.nan,
        "max_in_plane_delta_pixels": np.nan,
        "geometry_status": "",
        "error": "",
    }

    try:
        if not seg_path.exists():
            raise FileNotFoundError("SEG path does not exist")

        ds = pydicom.dcmread(str(seg_path), force=True)
        result["SEG_FrameOfReferenceUID"] = str(
            getattr(ds, "FrameOfReferenceUID", "")
        )
        frames = getattr(ds, "PerFrameFunctionalGroupsSequence", [])
        result["SEG_frames"] = len(frames)

        frame_refs = []
        frame_positions = []

        for frame in frames:
            refs = []
            for deriv in getattr(frame, "DerivationImageSequence", []):
                for src in getattr(deriv, "SourceImageSequence", []):
                    uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
                    if uid:
                        refs.append(uid)

            pos = vals(frame, "PlanePositionSequence", "ImagePositionPatient")
            for uid in refs:
                frame_refs.append((uid, pos))

            if refs and pos is not None:
                result["frames_with_source_CT_reference"] += 1
                frame_positions.append((refs[0], pos))

        local_pairs = [
            (uid, pos, ct_index[uid])
            for uid, pos in frame_positions if uid in ct_index
        ]
        result["source_refs_found_locally"] = len(local_pairs)

        if not local_pairs:
            result["geometry_status"] = "NO_FRAME_LEVEL_CT_REFERENCES_RESOLVED"
            rows.append(result)
            continue

        same_patient = []
        same_series = []
        for uid, pos, ct in local_pairs:
            same_patient.append(ct["patient"] == patient)
            same_series.append(ct["series"] == resolved_series)

        result["same_patient"] = all(same_patient)
        result["same_series"] = all(same_series)

        first_ct = local_pairs[0][2]
        result["CT_FrameOfReferenceUID"] = first_ct["for_uid"]
        result["frame_of_reference_match"] = (
            bool(result["SEG_FrameOfReferenceUID"])
            and result["SEG_FrameOfReferenceUID"] == first_ct["for_uid"]
        )

        orientation_ok = []
        spacing_ok = []
        pos_deltas = []
        in_plane_pixels = []

        for uid, seg_pos, ct in local_pairs:
            if len(ct["iop"]) == 6:
                # Compare orientation using the six DICOM direction cosines.
                seg_iop = vals(
                    ds.SharedFunctionalGroupsSequence[0],
                    "PlaneOrientationSequence",
                    "ImageOrientationPatient"
                ) if getattr(ds, "SharedFunctionalGroupsSequence", []) else None
                if seg_iop is not None and len(seg_iop) == 6:
                    orientation_ok.append(
                        np.allclose(seg_iop, ct["iop"], atol=1e-4)
                    )

            if len(ct["spacing"]) == 2:
                seg_spacing = vals(
                    ds.SharedFunctionalGroupsSequence[0],
                    "PixelMeasuresSequence",
                    "PixelSpacing"
                ) if getattr(ds, "SharedFunctionalGroupsSequence", []) else None
                if seg_spacing is not None and len(seg_spacing) == 2:
                    spacing_ok.append(
                        np.allclose(seg_spacing, ct["spacing"], atol=1e-4)
                    )

            if seg_pos is not None and len(seg_pos) == 3 and len(ct["ipp"]) == 3:
                delta = seg_pos - ct["ipp"]
                pos_deltas.append(float(np.linalg.norm(delta)))

                if len(ct["iop"]) == 6 and len(ct["spacing"]) == 2:
                    row_dir = ct["iop"][:3]
                    col_dir = ct["iop"][3:]
                    dx = float(np.dot(delta, row_dir)) / ct["spacing"][1]
                    dy = float(np.dot(delta, col_dir)) / ct["spacing"][0]
                    in_plane_pixels.append(float(np.hypot(dx, dy)))

        result["orientation_match"] = (
            all(orientation_ok) if orientation_ok else ""
        )
        result["pixel_spacing_match"] = (
            all(spacing_ok) if spacing_ok else ""
        )

        if pos_deltas:
            result["max_position_delta_mm"] = max(pos_deltas)
            result["position_match_within_0.1mm"] = (
                max(pos_deltas) <= 0.1
            )
        if in_plane_pixels:
            result["max_in_plane_delta_pixels"] = max(in_plane_pixels)

        if (
            result["same_patient"] is True
            and result["same_series"] is True
            and result["frame_of_reference_match"] is True
            and result["orientation_match"] is True
            and result["pixel_spacing_match"] is True
            and result["position_match_within_0.1mm"] is True
        ):
            result["geometry_status"] = "GEOMETRY_MATCHES_REFERENCED_CT"
        else:
            result["geometry_status"] = "REVIEW_REQUIRED"

    except Exception as exc:
        result["error"] = repr(exc)
        result["geometry_status"] = "AUDIT_ERROR"

    rows.append(result)

df = pd.DataFrame(rows)
df.to_csv(out_file, index=False)

print("\n=== GEOMETRY STATUS COUNTS ===")
print(df["geometry_status"].value_counts(dropna=False).to_string())

print("\n=== REFERENCE / GEOMETRY SUMMARY ===")
for col in [
    "link_status", "frame_of_reference_match", "orientation_match",
    "pixel_spacing_match", "position_match_within_0.1mm"
]:
    if col in df.columns:
        print(f"\n{col}:")
        print(df[col].value_counts(dropna=False).to_string())

print("\n=== CASES NEEDING REVIEW ===")
cols = [
    "PatientID", "link_status", "geometry_status",
    "frame_of_reference_match", "orientation_match",
    "pixel_spacing_match", "position_match_within_0.1mm",
    "max_position_delta_mm", "max_in_plane_delta_pixels", "error"
]
print(df[cols].to_string(index=False))

print("\nSaved:", out_file)
