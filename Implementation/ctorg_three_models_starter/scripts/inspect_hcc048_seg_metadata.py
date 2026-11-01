import pydicom
from pathlib import Path

path = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC"
    r"\hcc_tace_seg\HCC_048"
    r"\1.3.6.1.4.1.14519.5.2.1.1706.8374.191238202133507320458118565112"
    r"\1.3.6.1.4.1.14519.5.2.1.1706.8374.299766419358710200971072115544"
    r"\08c174be-7d19-474b-a435-0d4188681342.dcm"
)

ds = pydicom.dcmread(str(path), stop_before_pixels=True)

for key in [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "FrameOfReferenceUID",
    "SeriesDescription",
    "Modality",
    "ImageOrientationPatient",
    "PixelSpacing",
    "SliceThickness",
    "SpacingBetweenSlices",
    "NumberOfFrames",
]:
    print("{}: {}".format(key, getattr(ds, key, "MISSING")))

print("\nReferencedSeriesSequence present:",
      hasattr(ds, "ReferencedSeriesSequence"))

print("SharedFunctionalGroupsSequence present:",
      hasattr(ds, "SharedFunctionalGroupsSequence"))

print("PerFrameFunctionalGroupsSequence present:",
      hasattr(ds, "PerFrameFunctionalGroupsSequence"))
