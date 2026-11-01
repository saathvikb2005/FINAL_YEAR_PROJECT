import pydicom
import numpy as np
import pandas as pd
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_048")
out = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit")
out.mkdir(parents=True, exist_ok=True)

ct_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.212512542241432476118639218381"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
                "Modality", "") == "SEG"
)
seg = pydicom.dcmread(str(seg_path), force=True)
pixels = seg.pixel_array

ct_files = []
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT" and str(d.SeriesInstanceUID) == ct_uid:
            ct_files.append(d)
    except Exception:
        pass

ct_files.sort(key=lambda d: float(d.ImagePositionPatient[2]))
ct_by_z = {round(float(d.ImagePositionPatient[2]), 3): d for d in ct_files}

shared = seg.SharedFunctionalGroupsSequence[0]
seg_iop = np.asarray(shared.PlaneOrientationSequence[0].ImageOrientationPatient, float)
seg_spacing = np.asarray(shared.PixelMeasuresSequence[0].PixelSpacing, float)
seg_row_dir, seg_col_dir = seg_iop[:3], seg_iop[3:]

# Segment number 2 is the tumor/mass label in this dataset.
tumor_segment_number = 2
segment_frames = {}
for frame_idx, fg in enumerate(seg.PerFrameFunctionalGroupsSequence):
    refs = fg.SegmentIdentificationSequence[0]
    if int(refs.ReferencedSegmentNumber) == tumor_segment_number:
        segment_frames[frame_idx] = fg

rows = []
for frame_idx, fg in segment_frames.items():
    mask = pixels[frame_idx] > 0
    count = int(mask.sum())
    if count == 0:
        continue

    ipp = np.asarray(fg.PlanePositionSequence[0].ImagePositionPatient, float)
    z = round(float(ipp[2]), 3)
    ct = ct_by_z.get(z)
    if ct is None:
        continue

    ct_iop = np.asarray(ct.ImageOrientationPatient, float)
    ct_spacing = np.asarray(ct.PixelSpacing, float)
    ct_origin = np.asarray(ct.ImagePositionPatient, float)
    ct_row_dir, ct_col_dir = ct_iop[:3], ct_iop[3:]

    rr, cc = np.where(mask)
    # Sample boundary points and center, keeping this audit lightweight.
    points = np.array([
        [rr.min(), cc.min()],
        [rr.min(), cc.max()],
        [rr.max(), cc.min()],
        [rr.max(), cc.max()],
        [int(np.median(rr)), int(np.median(cc))]
    ], dtype=float)

    mapped_rows, mapped_cols = [], []
    for r, c in points:
        physical = (
            ipp
            + r * seg_spacing[0] * seg_row_dir
            + c * seg_spacing[1] * seg_col_dir
        )
        delta = physical - ct_origin
        mapped_rows.append(float(np.dot(delta, ct_row_dir) / ct_spacing[0]))
        mapped_cols.append(float(np.dot(delta, ct_col_dir) / ct_spacing[1]))

    rows.append({
        "seg_frame_1based": frame_idx + 1,
        "z_mm": z,
        "tumor_pixels": count,
        "seg_origin_x": float(ipp[0]),
        "seg_origin_y": float(ipp[1]),
        "ct_origin_x": float(ct_origin[0]),
        "ct_origin_y": float(ct_origin[1]),
        "row_shift_min": min(mapped_rows),
        "row_shift_max": max(mapped_rows),
        "col_shift_min": min(mapped_cols),
        "col_shift_max": max(mapped_cols),
        "all_sample_points_in_bounds": all(
            0 <= r < int(ct.Rows) and 0 <= c < int(ct.Columns)
            for r, c in zip(mapped_rows, mapped_cols)
        ),
    })

df = pd.DataFrame(rows)
path = out / "hcc048_tumor_inplane_projection_audit.csv"
df.to_csv(path, index=False)

print("Tumor-positive frames audited:", len(df))
print("CSV:", path)
if len(df):
    print(df[[
        "seg_frame_1based", "z_mm", "tumor_pixels",
        "row_shift_min", "row_shift_max",
        "col_shift_min", "col_shift_max",
        "all_sample_points_in_bounds"
    ]].to_string(index=False))
