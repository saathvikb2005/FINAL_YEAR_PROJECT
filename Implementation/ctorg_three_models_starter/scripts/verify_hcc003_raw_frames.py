import pydicom
import numpy as np
from pathlib import Path

root = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC"
    r"\hcc_tace_seg\HCC_003"
)

seg_path = next(
    p for p in root.rglob("*.dcm")
    if pydicom.dcmread(
        str(p), stop_before_pixels=True, force=True
    ).Modality == "SEG"
)

ds = pydicom.dcmread(str(seg_path))
arr = ds.pixel_array

print("SEG:", seg_path)
print("Pixel array shape:", arr.shape)

print("\nSegment definitions:")
for s in ds.SegmentSequence:
    print(
        "Number:", s.SegmentNumber,
        "| Label:", s.SegmentLabel,
        "| Description:", getattr(s, "SegmentDescription", "MISSING")
    )

print("\nFrame checks:")
for idx in [103, 124, 144]:  # zero-based: frames 104, 125, 145
    frame = ds.PerFrameFunctionalGroupsSequence[idx]
    seg_no = int(
        frame.SegmentIdentificationSequence[0].ReferencedSegmentNumber
    )
    pos = frame.PlanePositionSequence[0].ImagePositionPatient
    mask = arr[idx] > 0
    count = int(mask.sum())

    if count:
        rr, cc = np.where(mask)
        bbox = (
            int(rr.min()), int(rr.max()),
            int(cc.min()), int(cc.max())
        )
    else:
        bbox = None

    print(
        "Frame:", idx + 1,
        "| Segment:", seg_no,
        "| Z:", float(pos[2]),
        "| Pixels:", count,
        "| Bounding box (row_min,row_max,col_min,col_max):", bbox
    )
