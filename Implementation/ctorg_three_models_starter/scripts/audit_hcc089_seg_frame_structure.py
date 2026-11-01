from pathlib import Path
from collections import Counter, defaultdict
import pydicom
import numpy as np

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
seg_path = root / (
    r"HCC_089\1.3.6.1.4.1.14519.5.2.1.1706.8374.324511982524894820763579219177"
    r"\1.2.276.0.7230010.3.1.3.8323329.2303.1600929169.408163"
    r"\c25aaa91-f29d-4b21-899d-83da89c31303.dcm"
)

ds = pydicom.dcmread(str(seg_path))
frames = ds.PerFrameFunctionalGroupsSequence
pixels = ds.pixel_array

print("Pixel array shape:", pixels.shape)
print("SEG frames:", len(frames))

segment_counts = Counter()
position_counts = Counter()
nonzero_counts = defaultdict(list)
sample_rows = []

for i, fg in enumerate(frames):
    seg_num = None
    sid = getattr(fg, "SegmentIdentificationSequence", [])
    if sid:
        seg_num = int(sid[0].ReferencedSegmentNumber)

    pos = None
    pseq = getattr(fg, "PlanePositionSequence", [])
    if pseq:
        pos = tuple(round(float(v), 3) for v in pseq[0].ImagePositionPatient)

    refs = []
    for deriv in getattr(fg, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
            if uid:
                refs.append(uid)

    count = int(np.count_nonzero(pixels[i]))
    segment_counts[seg_num] += 1
    position_counts[pos] += 1
    if seg_num is not None:
        nonzero_counts[seg_num].append(count)

    if i < 12 or i in (94, 95, 189, 190, 284, 285, 378, 379):
        sample_rows.append((i + 1, seg_num, pos, count, refs))

print("\nFrames per segment number:")
for k, v in sorted(segment_counts.items(), key=lambda x: str(x[0])):
    vals = nonzero_counts[k]
    print(f"  Segment {k}: frames={v}, nonzero_min={min(vals) if vals else 0}, "
          f"nonzero_median={float(np.median(vals)) if vals else 0}, "
          f"nonzero_max={max(vals) if vals else 0}")

valid_positions = [p for p in position_counts if p is not None]
print("\nUnique physical positions:", len(valid_positions))
print("Repeated position groups:", sum(1 for n in position_counts.values() if n > 1))
print("Most common positions:", position_counts.most_common(8))

print("\nSelected frames:")
for frame, seg, pos, count, refs in sample_rows:
    print(f"  frame={frame}, segment={seg}, position={pos}, "
          f"positive_pixels={count}, refs={refs}")

print("\nFirst and last 12 frame positions:")
for i in list(range(min(12, len(frames)))) + list(range(max(12, len(frames)-12), len(frames))):
    fg = frames[i]
    pseq = getattr(fg, "PlanePositionSequence", [])
    pos = [float(v) for v in pseq[0].ImagePositionPatient] if pseq else None
    sid = getattr(fg, "SegmentIdentificationSequence", [])
    seg = int(sid[0].ReferencedSegmentNumber) if sid else None
    print(f"  frame={i+1}, segment={seg}, position={pos}")
