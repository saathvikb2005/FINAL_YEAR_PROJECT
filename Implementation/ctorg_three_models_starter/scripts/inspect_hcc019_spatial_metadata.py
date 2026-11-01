import pydicom
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_019")

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
               "Modality", "") == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True, force=True)

print("SEG top-level spatial metadata:")
for tag in [
    "ImagePositionPatient", "ImageOrientationPatient", "PixelSpacing",
    "Rows", "Columns", "FrameOfReferenceUID", "SpatialLocationsPreserved",
    "ContentLabel", "ContentDescription", "DerivationDescription"
]:
    print(f"{tag}: {getattr(seg, tag, '<absent>')}")

print("\nSEG dimension organization:")
for tag in [
    "DimensionOrganizationSequence",
    "DimensionIndexSequence",
    "SharedFunctionalGroupsSequence"
]:
    value = getattr(seg, tag, None)
    print(f"{tag}: {'present' if value is not None else '<absent>'}")

print("\nFirst per-frame position and source reference:")
fg = seg.PerFrameFunctionalGroupsSequence[0]
print("PlanePositionSequence:",
      getattr(fg, "PlanePositionSequence", "<absent>"))
print("DerivationImageSequence:",
      getattr(fg, "DerivationImageSequence", "<absent>"))
print("")

print("SEG file:", seg_path)
