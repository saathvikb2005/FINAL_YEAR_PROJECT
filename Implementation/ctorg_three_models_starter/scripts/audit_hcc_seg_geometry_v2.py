from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
import pydicom

DATA_ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
AUDIT_ROOT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit")

LINK_FILE = AUDIT_ROOT / "hcc_ct_seg_linkage_new_download.csv"
OUT_FILE = AUDIT_ROOT / "hcc_ct_seg_geometry_alignment_v2.csv"

# Numerical tolerances: geometry review criteria, not clinical validation.
POSITION_TOL_MM = 0.2
SPACING_TOL_MM = 0.001
ORIENTATION_TOL = 0.001
Z_TOL_MM = 0.1


def arr(value):
    return np.asarray(value, dtype=float)


def get_first_sequence_value(obj, sequence_name, field):
    seq = getattr(obj, sequence_name, [])
    if seq and hasattr(seq[0], field):
        return arr(getattr(seq[0], field))
    return None


def grid_corners(position, orientation, spacing, rows, cols):
    """Four image-pixel-center corners in DICOM patient coordinates."""
    row_dir = orientation[:3]
    col_dir = orientation[3:]
    row_step = spacing[0] * row_dir
    col_step = spacing[1] * col_dir
    origin = position
    return np.array([
        origin,
        origin + (cols - 1) * col_step,
        origin + (rows - 1) * row_step,
        origin + (cols - 1) * col_step + (rows - 1) * row_step,
    ])


def main():
    links = pd.read_csv(LINK_FILE, dtype=str).fillna("")

    # Index CT instances by SOP Instance UID.
    ct_index = {}
    for path in DATA_ROOT.rglob("*.dcm"):
        try:
            ds = pydicom.dcmread(
                str(path), stop_before_pixels=True, force=True,
                specific_tags=[
                    "Modality", "SOPInstanceUID", "SeriesInstanceUID",
                    "PatientID", "FrameOfReferenceUID",
                    "ImagePositionPatient", "ImageOrientationPatient",
                    "PixelSpacing", "Rows", "Columns",
                ],
            )
            if str(getattr(ds, "Modality", "")).upper() != "CT":
                continue
            uid = str(getattr(ds, "SOPInstanceUID", ""))
            if uid:
                ct_index[uid] = {
                    "path": path,
                    "patient": str(getattr(ds, "PatientID", "")),
                    "series": str(getattr(ds, "SeriesInstanceUID", "")),
                    "for_uid": str(getattr(ds, "FrameOfReferenceUID", "")),
                    "pos": arr(getattr(ds, "ImagePositionPatient", [])),
                    "ori": arr(getattr(ds, "ImageOrientationPatient", [])),
                    "spacing": arr(getattr(ds, "PixelSpacing", [])),
                    "rows": int(getattr(ds, "Rows", 0)),
                    "cols": int(getattr(ds, "Columns", 0)),
                }
        except Exception:
            continue

    print("Indexed local CT instances:", len(ct_index))
    output = []

    for _, link in links.iterrows():
        patient = link.get("PatientID", "")
        seg_path = Path(link.get("SEG_path", ""))
        record = {
            "PatientID": patient,
            "SEG_path": str(seg_path),
            "link_status": link.get("link_status", ""),
            "resolved_CT_series": link.get("resolved_local_CT_series", ""),
            "SEG_frames": 0,
            "frames_with_references": 0,
            "unique_referenced_CT_SOPs": 0,
            "referenced_CT_SOPs_found_locally": 0,
            "same_patient_all_refs": False,
            "same_resolved_series_all_refs": False,
            "frame_of_reference_match": False,
            "orientation_match_or_reversed": False,
            "pixel_spacing_match": False,
            "max_corner_error_mm": np.nan,
            "max_z_error_mm": np.nan,
            "max_spacing_error_mm": np.nan,
            "max_orientation_error": np.nan,
            "source_comparisons": 0,
            "comparisons_passing_tolerance": 0,
            "geometry_v2_status": "REVIEW_REQUIRED",
            "error": "",
        }

        try:
            if not seg_path.exists():
                raise FileNotFoundError(f"SEG file not found: {seg_path}")

            seg = pydicom.dcmread(str(seg_path), force=True)
            frames = getattr(seg, "PerFrameFunctionalGroupsSequence", [])
            record["SEG_frames"] = len(frames)

            shared_seq = getattr(seg, "SharedFunctionalGroupsSequence", [])
            if not shared_seq:
                raise ValueError("SEG lacks SharedFunctionalGroupsSequence")

            shared = shared_seq[0]
            seg_ori = get_first_sequence_value(
                shared, "PlaneOrientationSequence", "ImageOrientationPatient"
            )
            seg_spacing = get_first_sequence_value(
                shared, "PixelMeasuresSequence", "PixelSpacing"
            )

            if seg_ori is None or len(seg_ori) != 6:
                raise ValueError("Missing/invalid shared SEG orientation")
            if seg_spacing is None or len(seg_spacing) != 2:
                raise ValueError("Missing/invalid shared SEG pixel spacing")

            seg_for = str(getattr(seg, "FrameOfReferenceUID", ""))
            refs_seen = set()
            patients_ok, series_ok, for_ok = [], [], []
            corner_errors, z_errors, spacing_errors, orientation_errors = [], [], [], []
            comparisons = 0
            passing = 0
            frames_with_refs = 0

            for frame_no, frame in enumerate(frames, start=1):
                seg_pos = get_first_sequence_value(
                    frame, "PlanePositionSequence", "ImagePositionPatient"
                )
                if seg_pos is None or len(seg_pos) != 3:
                    continue

                frame_uids = set()
                for deriv in getattr(frame, "DerivationImageSequence", []):
                    for src in getattr(deriv, "SourceImageSequence", []):
                        uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
                        if uid:
                            frame_uids.add(uid)

                if not frame_uids:
                    continue

                frames_with_refs += 1
                for uid in frame_uids:
                    refs_seen.add(uid)
                    ct = ct_index.get(uid)
                    if ct is None:
                        continue

                    patients_ok.append(ct["patient"] == patient)
                    series_ok.append(
                        ct["series"] == record["resolved_CT_series"]
                    )
                    for_ok.append(bool(seg_for) and seg_for == ct["for_uid"])

                    if len(ct["pos"]) != 3 or len(ct["ori"]) != 6 or len(ct["spacing"]) != 2:
                        continue

                    # Compare the physical image-plane corner sets. This handles
                    # matching or reversed orientation without assuming either.
                    seg_corners = grid_corners(
                        seg_pos, seg_ori, seg_spacing,
                        int(getattr(seg, "Rows", 0)),
                        int(getattr(seg, "Columns", 0)),
                    )
                    ct_corners = grid_corners(
                        ct["pos"], ct["ori"], ct["spacing"],
                        ct["rows"], ct["cols"],
                    )

                    # Corresponding pixel-grid corners must coincide. Find the
                    # best one-to-one corner correspondence for orientation.
                    distances = np.linalg.norm(
                        seg_corners[:, None, :] - ct_corners[None, :, :], axis=2
                    )
                    best_corner_error = min(
                        max(distances[i, j] for i, j in enumerate(perm))
                        for perm in (
                            (0, 1, 2, 3),
                            (0, 1, 3, 2),
                            (0, 2, 1, 3),
                            (0, 2, 3, 1),
                            (0, 3, 1, 2),
                            (0, 3, 2, 1),
                            (1, 0, 2, 3),
                            (1, 0, 3, 2),
                            (1, 2, 0, 3),
                            (1, 2, 3, 0),
                            (1, 3, 0, 2),
                            (1, 3, 2, 0),
                            (2, 0, 1, 3),
                            (2, 0, 3, 1),
                            (2, 1, 0, 3),
                            (2, 1, 3, 0),
                            (2, 3, 0, 1),
                            (2, 3, 1, 0),
                            (3, 0, 1, 2),
                            (3, 0, 2, 1),
                            (3, 1, 0, 2),
                            (3, 1, 2, 0),
                            (3, 2, 0, 1),
                            (3, 2, 1, 0),
                        )
                    )
                    z_error = abs(float(seg_pos[2] - ct["pos"][2]))
                    spacing_error = float(np.max(np.abs(seg_spacing - ct["spacing"])))

                    # Orientation may match directly or be reversed.
                    direct_ori_error = float(np.max(np.abs(seg_ori - ct["ori"])))
                    reversed_ori_error = float(np.max(np.abs(seg_ori + ct["ori"])))
                    orientation_error = min(direct_ori_error, reversed_ori_error)

                    corner_errors.append(best_corner_error)
                    z_errors.append(z_error)
                    spacing_errors.append(spacing_error)
                    orientation_errors.append(orientation_error)
                    comparisons += 1

                    if (
                        best_corner_error <= POSITION_TOL_MM
                        and z_error <= Z_TOL_MM
                        and spacing_error <= SPACING_TOL_MM
                        and orientation_error <= ORIENTATION_TOL
                        and seg_ori.shape == ct["ori"].shape
                    ):
                        passing += 1

            record["frames_with_references"] = frames_with_refs
            record["unique_referenced_CT_SOPs"] = len(refs_seen)
            record["referenced_CT_SOPs_found_locally"] = sum(
                uid in ct_index for uid in refs_seen
            )
            record["same_patient_all_refs"] = bool(patients_ok) and all(patients_ok)
            record["same_resolved_series_all_refs"] = bool(series_ok) and all(series_ok)
            record["frame_of_reference_match"] = bool(for_ok) and all(for_ok)
            record["source_comparisons"] = comparisons
            record["comparisons_passing_tolerance"] = passing
            record["max_corner_error_mm"] = max(corner_errors) if corner_errors else np.nan
            record["max_z_error_mm"] = max(z_errors) if z_errors else np.nan
            record["max_spacing_error_mm"] = max(spacing_errors) if spacing_errors else np.nan
            record["max_orientation_error"] = max(orientation_errors) if orientation_errors else np.nan
            record["orientation_match_or_reversed"] = (
                bool(orientation_errors) and max(orientation_errors) <= ORIENTATION_TOL
            )
            record["pixel_spacing_match"] = (
                bool(spacing_errors) and max(spacing_errors) <= SPACING_TOL_MM
            )

            if comparisons == 0:
                record["geometry_v2_status"] = "NO_LOCAL_SOURCE_COMPARISONS"
            elif passing == comparisons and record["same_patient_all_refs"] and record["same_resolved_series_all_refs"]:
                record["geometry_v2_status"] = "SOURCE_GRID_GEOMETRY_MATCHES"
            else:
                record["geometry_v2_status"] = "REVIEW_REQUIRED"

        except Exception as exc:
            record["error"] = repr(exc)
            record["geometry_v2_status"] = "AUDIT_ERROR"

        output.append(record)
        print(
            patient,
            record["geometry_v2_status"],
            f'{record["comparisons_passing_tolerance"]}/{record["source_comparisons"]}',
        )

    pd.DataFrame(output).to_csv(OUT_FILE, index=False)
    print("\n=== V2 geometry status counts ===")
    print(pd.DataFrame(output)["geometry_v2_status"].value_counts(dropna=False).to_string())
    print("\nSaved:", OUT_FILE)


if __name__ == "__main__":
    main()
