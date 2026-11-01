from pathlib import Path
import csv
import numpy as np
import pydicom

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc_tumor_pixel_diagnostic.csv")
PATIENTS = ("HCC_003", "HCC_019", "HCC_012")

def frame_segment(fg):
    try:
        return int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    except Exception:
        return None

def frame_refs(fg):
    result = []
    for deriv in getattr(fg, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
            if uid:
                result.append(uid)
    return result

OUT.parent.mkdir(parents=True, exist_ok=True)
rows = []

for patient in PATIENTS:
    print(f"\n========== {patient} ==========")
    seg_paths, ct_paths = [], []

    for p in (ROOT / patient).rglob("*.dcm"):
        try:
            ds = pydicom.dcmread(p, stop_before_pixels=True)
            if ds.Modality == "SEG":
                seg_paths.append(p)
            elif ds.Modality == "CT":
                ct_paths.append(p)
        except Exception:
            continue

    ct_by_uid = {}
    for p in ct_paths:
        try:
            ds = pydicom.dcmread(p)
            ct_by_uid[str(ds.SOPInstanceUID)] = ds
        except Exception as exc:
            print("CT decode warning:", p.name, str(exc)[:120])

    for seg_path in seg_paths:
        seg = pydicom.dcmread(seg_path)
        pixel_array = seg.pixel_array
        groups = seg.PerFrameFunctionalGroupsSequence

        print("SEG:", seg_path.name)
        print("Decoded SEG shape:", pixel_array.shape)
        print("SEG frame count:", len(groups))
        print("SEG pixel dtype:", pixel_array.dtype)
        print("SEG unique pixel values:", np.unique(pixel_array)[:10])

        if pixel_array.ndim != 3 or pixel_array.shape[0] != len(groups):
            print("WARNING: unexpected SEG pixel-array shape; stopping this SEG.")
            continue

        tumor_frames = 0
        tumor_pixels = 0
        matched_ct = 0
        shape_mismatch = 0

        for i, fg in enumerate(groups):
            segment = frame_segment(fg)
            mask = pixel_array[i] > 0 if segment == 2 else None

            if segment == 2:
                tumor_frames += 1
                tumor_pixels += int(mask.sum())

            refs = frame_refs(fg)
            resolved = [ct_by_uid[uid] for uid in refs if uid in ct_by_uid]

            if not resolved:
                rows.append({
                    "PatientID": patient, "frame": i + 1,
                    "segment_number": segment,
                    "tumor_pixels": int(mask.sum()) if mask is not None else 0,
                    "referenced_CT_count": len(refs),
                    "resolved_CT_count": 0,
                    "CT_rows": "", "CT_columns": "",
                    "SEG_rows": int(pixel_array.shape[1]),
                    "SEG_columns": int(pixel_array.shape[2]),
                    "dimensions_match": False
                })
                continue

            matched_ct += 1
            for ct in resolved:
                same_shape = (
                    int(ct.Rows) == pixel_array.shape[1] and
                    int(ct.Columns) == pixel_array.shape[2]
                )
                if not same_shape:
                    shape_mismatch += 1

                rows.append({
                    "PatientID": patient, "frame": i + 1,
                    "segment_number": segment,
                    "tumor_pixels": int(mask.sum()) if mask is not None else 0,
                    "referenced_CT_count": len(refs),
                    "resolved_CT_count": len(resolved),
                    "CT_rows": int(ct.Rows),
                    "CT_columns": int(ct.Columns),
                    "SEG_rows": int(pixel_array.shape[1]),
                    "SEG_columns": int(pixel_array.shape[2]),
                    "dimensions_match": same_shape
                })

        print("Tumor-segment frames:", tumor_frames)
        print("Total tumor-positive pixels across segment-2 frames:", tumor_pixels)
        print("Frames with at least one resolved referenced CT:", matched_ct)
        print("CT/SEG dimension mismatches:", shape_mismatch)

with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    if rows:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

print("\nCSV saved to:", OUT)
print("Diagnostic rows:", len(rows))
