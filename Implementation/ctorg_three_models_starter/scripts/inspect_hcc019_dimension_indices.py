import pydicom
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_019")

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
               "Modality", "") == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True, force=True)

print("=== Dimension Index Sequence ===")
for i, item in enumerate(seg.DimensionIndexSequence, start=1):
    print(f"Index {i}:")
    print("  DimensionOrganizationUID:",
          getattr(item, "DimensionOrganizationUID", "<absent>"))
    print("  DimensionIndexPointer:",
          getattr(item, "DimensionIndexPointer", "<absent>"))
    print("  FunctionalGroupPointer:",
          getattr(item, "FunctionalGroupPointer", "<absent>"))
    print("  DescriptionLabel:",
          getattr(item, "DimensionDescriptionLabel", "<absent>"))

print("\n=== First 5 frame content entries ===")
for i, fg in enumerate(seg.PerFrameFunctionalGroupsSequence[:5], start=1):
    print(f"Frame {i}:")
    for item in getattr(fg, "FrameContentSequence", []):
        print("  DimensionIndexValues:",
              getattr(item, "DimensionIndexValues", "<absent>"))
        print("  InStackPositionNumber:",
              getattr(item, "InStackPositionNumber", "<absent>"))
        print("  TemporalPositionIndex:",
              getattr(item, "TemporalPositionIndex", "<absent>"))
    for item in getattr(fg, "SegmentIdentificationSequence", []):
        print("  ReferencedSegmentNumber:",
              getattr(item, "ReferencedSegmentNumber", "<absent>"))

print("\n=== Shared plane geometry ===")
shared = seg.SharedFunctionalGroupsSequence[0]
for tag in ["PlaneOrientationSequence", "PixelMeasuresSequence"]:
    print(tag, getattr(shared, tag, "<absent>"))
