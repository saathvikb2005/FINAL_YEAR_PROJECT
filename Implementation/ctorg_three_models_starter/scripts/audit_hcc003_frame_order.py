import pydicom
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter

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

segments = {
    int(s.SegmentNumber): s.SegmentLabel
    for s in ds.SegmentSequence
}
groups = defaultdict(list)

for i, frame in enumerate(ds.PerFrameFunctionalGroupsSequence):
    seg_no = int(
        frame.SegmentIdentificationSequence[0].ReferencedSegmentNumber
    )
    pos = np.asarray(
        frame.PlanePositionSequence[0].ImagePositionPatient,
        dtype=float
    )
    count = int(np.count_nonzero(arr[i]))
    groups[seg_no].append((i + 1, float(pos[2]), count, pos.tolist()))

print("SEG:", seg_path)
print("Total frames:", len(ds.PerFrameFunctionalGroupsSequence))
print("Pixel array:", arr.shape)

for seg_no in sorted(groups):
    records = groups[seg_no]
    z_values = [round(r[1], 3) for r in records]
    unique_z = sorted(set(z_values))
    diffs = np.diff(unique_z)
    positive = [r for r in records if r[2] > 0]
    duplicate_count = len(z_values) - len(set(z_values))

    print("\nSEGMENT", seg_no, segments.get(seg_no, "UNKNOWN"))
    print("Frame count:", len(records))
    print("Positive frames:", len(positive))
    print("Total positive pixels:", sum(r[2] for r in records))
    print("Z range:", min(z_values), "to", max(z_values))
    print("Unique Z positions:", len(unique_z))
    print("Duplicate Z entries within segment:", duplicate_count)
    print("Smallest/largest Z step:", (
        round(float(diffs.min()), 3),
        round(float(diffs.max()), 3)
    ) if len(diffs) else "N/A")
    print("First 8 frames (frame, Z, pixels):",
          [(r[0], r[1], r[2]) for r in records[:8]])
    print("Last 8 frames (frame, Z, pixels):",
          [(r[0], r[1], r[2]) for r in records[-8:]])
    print("First 8 positive frames:",
          [(r[0], r[1], r[2]) for r in positive[:8]])

print("\nFrame segment order:")
print(Counter(
    int(f.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    for f in ds.PerFrameFunctionalGroupsSequence
))
