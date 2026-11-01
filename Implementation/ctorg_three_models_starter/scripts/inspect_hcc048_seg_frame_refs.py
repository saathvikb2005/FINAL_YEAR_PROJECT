import pydicom
from pathlib import Path
from collections import Counter

path = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC"
    r"\hcc_tace_seg\HCC_048"
    r"\1.3.6.1.4.1.14519.5.2.1.1706.8374.191238202133507320458118565112"
    r"\1.3.6.1.4.1.14519.5.2.1.1706.8374.299766419358710200971072115544"
    r"\08c174be-7d19-474b-a435-0d4188681342.dcm"
)

ds = pydicom.dcmread(str(path), stop_before_pixels=True)

def show_group(group, title):
    print("\n" + title)
    for seq_name in [
        "PlaneOrientationSequence",
        "PixelMeasuresSequence",
        "PlanePositionSequence",
        "DerivationImageSequence",
        "SegmentIdentificationSequence",
        "FrameContentSequence",
    ]:
        seq = getattr(group, seq_name, None)
        if not seq:
            continue
        print(" ", seq_name)
        for item in seq[:1]:
            for key in [
                "ImageOrientationPatient",
                "PixelSpacing",
                "SliceThickness",
                "SpacingBetweenSlices",
                "ImagePositionPatient",
                "ReferencedSegmentNumber",
                "DimensionIndexValues",
            ]:
                if hasattr(item, key):
                    print("   ", key, "=", getattr(item, key))
            for deriv in getattr(item, "DerivationImageSequence", []):
                for src in getattr(deriv, "SourceImageSequence", []):
                    print("    Source SOP:", getattr(src, "ReferencedSOPInstanceUID", "MISSING"))
                    print("    Source class:", getattr(src, "ReferencedSOPClassUID", "MISSING"))

shared = getattr(ds, "SharedFunctionalGroupsSequence", [])
if shared:
    show_group(shared[0], "SHARED FUNCTIONAL GROUP")

frames = getattr(ds, "PerFrameFunctionalGroupsSequence", [])
print("\nPer-frame group count:", len(frames))

ref_counts = Counter()
frames_with_refs = 0

for i, frame in enumerate(frames):
    refs = []
    for deriv in getattr(frame, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = getattr(src, "ReferencedSOPInstanceUID", None)
            if uid:
                refs.append(uid)
                ref_counts[uid] += 1
    if refs:
        frames_with_refs += 1
    if i < 3 or refs:
        show_group(frame, "FRAME {}".format(i + 1))

print("\nFrames with source SOP references:", frames_with_refs, "/", len(frames))
print("Unique referenced SOP UIDs:", len(ref_counts))
for uid, count in ref_counts.most_common(10):
    print(" ", uid, "count=", count)
