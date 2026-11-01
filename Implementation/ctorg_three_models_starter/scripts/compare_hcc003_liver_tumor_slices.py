import pydicom
import numpy as np
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_003")

seg_path = next(
    p for p in base.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
ds = pydicom.dcmread(str(seg_path))
pixels = ds.pixel_array

# Segment 1 = Liver; Segment 2 = Mass/Tumor.
targets = [-260.0, -207.5, -157.5]

for z_target in targets:
    print(f"\n===== Z = {z_target} mm =====")

    masks = {}
    for i, fg in enumerate(ds.PerFrameFunctionalGroupsSequence):
        seg_no = int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
        z = float(fg.PlanePositionSequence[0].ImagePositionPatient[2])

        if abs(z - z_target) < 0.01 and seg_no in (1, 2):
            masks[seg_no] = pixels[i] > 0

    for seg_no, name in [(1, "Liver"), (2, "Mass/Tumor")]:
        if seg_no not in masks:
            print(name, "frame not found")
            continue

        mask = masks[seg_no]
        rr, cc = np.where(mask)

        if len(rr) == 0:
            print(f"{name}: EMPTY")
            continue

        print(
            f"{name}: pixels={len(rr)}, "
            f"bbox_rows={rr.min()}..{rr.max()}, "
            f"bbox_cols={cc.min()}..{cc.max()}"
        )

    if 1 in masks and 2 in masks:
        liver, tumor = masks[1], masks[2]
        intersection = int(np.logical_and(liver, tumor).sum())
        tumor_area = int(tumor.sum())
        liver_area = int(liver.sum())

        print("Same-grid intersection pixels:", intersection)
        print(
            "Tumor pixels inside liver mask (%):",
            round(100 * intersection / tumor_area, 2) if tumor_area else 0
        )
        print(
            "Liver pixels covered by tumor mask (%):",
            round(100 * intersection / liver_area, 2) if liver_area else 0
        )
