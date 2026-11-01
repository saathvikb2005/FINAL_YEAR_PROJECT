from pathlib import Path
from collections import Counter
import pydicom
import numpy as np

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
seg_path = root / (
    r"HCC_089\1.3.6.1.4.1.14519.5.2.1.1706.8374.324511982524894820763579219177"
    r"\1.2.276.0.7230010.3.1.3.8323329.2303.1600929169.408163"
    r"\c25aaa91-f29d-4b21-899d-83da89c31303.dcm"
)

ds = pydicom.dcmread(str(seg_path))
pixels = ds.pixel_array
frames = ds.PerFrameFunctionalGroupsSequence

print("SegmentationType:", getattr(ds, "SegmentationType", None))
print("BitsAllocated:", getattr(ds, "BitsAllocated", None))
print("BitsStored:", getattr(ds, "BitsStored", None))
print("HighBit:", getattr(ds, "HighBit", None))
print("PixelRepresentation:", getattr(ds, "PixelRepresentation", None))
print("Pixel array shape/dtype:", pixels.shape, pixels.dtype)
print("Global unique values:", np.unique(pixels, return_counts=True))

definitions = {}
for item in getattr(ds, "SegmentSequence", []):
    n = int(item.SegmentNumber)
    definitions[n] = str(getattr(item, "SegmentLabel", ""))

print("\nSegment definitions:")
for n, label in definitions.items():
    print(f"  {n}: {label}")

counts = Counter()
positive_by_segment = {n: [] for n in definitions}

for i, fg in enumerate(frames):
    sid = getattr(fg, "SegmentIdentificationSequence", [])
    seg_num = int(sid[0].ReferencedSegmentNumber) if sid else -1
    n = int(np.count_nonzero(pixels[i]))
    counts[seg_num] += n
    positive_by_segment.setdefault(seg_num, []).append(n)

print("\nNonzero pixel totals by segment:")
for n, label in definitions.items():
    values = positive_by_segment.get(n, [])
    print(
        f"  {n} ({label}): frames={len(values)}, "
        f"nonempty_frames={sum(v > 0 for v in values)}, "
        f"total_pixels={sum(values)}, max_per_frame={max(values) if values else 0}"
    )

print("\nFrame order check:")
for i in [0, 1, 2, 94, 95, 96, 189, 190, 284, 285, 379]:
    fg = frames[i]
    sid = getattr(fg, "SegmentIdentificationSequence", [])
    seg_num = int(sid[0].ReferencedSegmentNumber) if sid else -1
    print(f"  frame={i+1}, segment={seg_num}, nonzero={int(np.count_nonzero(pixels[i]))}")
