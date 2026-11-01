from pathlib import Path
import pydicom
from collections import Counter

seg_path = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg"
    r"\HCC_089\1.3.6.1.4.1.14519.5.2.1.1706.8374.324511982524894820763579219177"
    r"\1.2.276.0.7230010.3.1.3.8323329.2303.1600929169.408163"
    r"\c25aaa91-f29d-4b21-899d-83da89c31303.dcm"
)

ds = pydicom.dcmread(str(seg_path), stop_before_pixels=True)
print("SEG frames:", getattr(ds, "NumberOfFrames", "unknown"))
print("Shared functional groups:", len(getattr(ds, "SharedFunctionalGroupsSequence", [])))
print("Per-frame functional groups:", len(getattr(ds, "PerFrameFunctionalGroupsSequence", [])))

counts = Counter()
examples = []
per_frame = getattr(ds, "PerFrameFunctionalGroupsSequence", [])

for i, fg in enumerate(per_frame):
    derivation = getattr(fg, "DerivationImageSequence", [])
    refs = []
    for deriv in derivation:
        for source in getattr(deriv, "SourceImageSequence", []):
            uid = str(getattr(source, "ReferencedSOPInstanceUID", ""))
            if uid:
                refs.append(uid)
    counts[len(refs)] += 1
    if refs and len(examples) < 10:
        examples.append((i + 1, refs))

print("\nSource references per SEG frame:")
for n, count in sorted(counts.items()):
    print(f"  {n} reference(s): {count} frames")

print("\nFirst referenced-frame examples:")
for frame, refs in examples:
    print(f"  Frame {frame}: {refs}")

print("\nSEG shared orientation/position/spacing:")
shared = getattr(ds, "SharedFunctionalGroupsSequence", [])
if shared:
    fg = shared[0]
    for seq_name in (
        "PlaneOrientationSequence",
        "PixelMeasuresSequence",
        "PlanePositionSequence",
    ):
        seq = getattr(fg, seq_name, [])
        print(f"  {seq_name}:")
        if seq:
            item = seq[0]
            for attr in (
                "ImageOrientationPatient",
                "PixelSpacing",
                "SpacingBetweenSlices",
                "SliceThickness",
                "ImagePositionPatient",
            ):
                if hasattr(item, attr):
                    print(f"    {attr} = {getattr(item, attr)}")
