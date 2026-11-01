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

print("SEG file:", seg_path)
print("Shape:", arr.shape, "dtype:", arr.dtype)
print("Study UID:", ds.StudyInstanceUID)
print("Frame of Reference:", getattr(ds, "FrameOfReferenceUID", "MISSING"))

print("\nSegments:")
for s in ds.SegmentSequence:
    print(
        "Number:", s.SegmentNumber,
        "| Label:", s.SegmentLabel,
        "| Description:", getattr(s, "SegmentDescription", "MISSING")
    )

print("\nShared geometry:")
shared = ds.SharedFunctionalGroupsSequence[0]
for name in ["PlaneOrientationSequence", "PixelMeasuresSequence"]:
    seq = getattr(shared, name, [])
    if seq:
        print(name, seq[0])

print("\nPositive frames by segment:")
for seg_no in sorted({
    int(f.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    for f in ds.PerFrameFunctionalGroupsSequence
}):
    indices = [
        i for i, f in enumerate(ds.PerFrameFunctionalGroupsSequence)
        if int(f.SegmentIdentificationSequence[0].ReferencedSegmentNumber) == seg_no
    ]
    positive = []
    for i in indices:
        count = int(np.count_nonzero(arr[i]))
        if count:
            pos = ds.PerFrameFunctionalGroupsSequence[i].PlanePositionSequence[0].ImagePositionPatient
            positive.append((i + 1, round(float(pos[2]), 3), count))
    print("Segment", seg_no, "| frames:", len(indices), "| positive:", len(positive))
    print("First positive frames:", positive[:12])
