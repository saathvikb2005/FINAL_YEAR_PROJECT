import pydicom
import numpy as np
from pathlib import Path

root = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC"
    r"\hcc_tace_seg\HCC_003"
)
path = next(
    p for p in root.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
ds = pydicom.dcmread(str(path))
arr = ds.pixel_array

segments = {}
for s in ds.SegmentSequence:
    segments[int(s.SegmentNumber)] = s.SegmentLabel

print("Segment labels:", segments)

for z_target in [-260.0, -207.5, -157.5]:
    frame_by_seg = {}
    for i, frame in enumerate(ds.PerFrameFunctionalGroupsSequence):
        seg_no = int(frame.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
        z = float(frame.PlanePositionSequence[0].ImagePositionPatient[2])
        if abs(z - z_target) < 0.01:
            frame_by_seg[seg_no] = i

    print("\nZ =", z_target)
    masks = {}
    for seg_no in [1, 2, 3, 4]:
        if seg_no not in frame_by_seg:
            continue
        i = frame_by_seg[seg_no]
        mask = arr[i] > 0
        masks[seg_no] = mask
        print(
            "Segment", seg_no, segments.get(seg_no, "?"),
            "| frame", i + 1,
            "| pixels", int(mask.sum())
        )

    if 1 in masks and 2 in masks:
        liver = masks[1]
        mass = masks[2]
        intersection = int(np.logical_and(liver, mass).sum())
        union = int(np.logical_or(liver, mass).sum())
        print("Liver/Mass IoU:", round(intersection / union, 4) if union else 0)
        print("Mass contained in liver:", round(intersection / int(mass.sum()), 4) if mass.sum() else 0)
