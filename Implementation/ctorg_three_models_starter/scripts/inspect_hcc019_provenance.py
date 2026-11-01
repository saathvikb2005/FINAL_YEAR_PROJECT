import pydicom
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_019")

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
               "Modality", "") == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True, force=True)

print("=== SEG provenance ===")
for tag in [
    "Manufacturer", "ManufacturerModelName", "SoftwareVersions",
    "DeviceSerialNumber", "SOPClassUID", "SOPInstanceUID",
    "SeriesDescription", "SeriesNumber", "StudyDescription",
    "ContentDate", "ContentTime", "InstanceCreationDate",
    "InstanceCreationTime", "InstanceCreatorUID",
    "ConversionType", "SpecificCharacterSet"
]:
    print(f"{tag}: {getattr(seg, tag, '<absent>')}")

print("\n=== Segment definitions ===")
for item in seg.SegmentSequence:
    print(
        "Number:", getattr(item, "SegmentNumber", "<absent>"),
        "| Label:", getattr(item, "SegmentLabel", "<absent>"),
        "| AlgorithmType:", getattr(item, "SegmentAlgorithmType", "<absent>"),
        "| AlgorithmName:", getattr(item, "SegmentAlgorithmName", "<absent>")
    )

print("\n=== Referenced series/study metadata ===")
for tag in [
    "ReferencedSeriesSequence", "StudiesContainingOtherReferencedInstancesSequence",
    "ReferencedStudySequence", "CommonInstanceReferenceSequence"
]:
    value = getattr(seg, tag, None)
    print(f"{tag}: {'present' if value is not None else '<absent>'}")
    if value is not None:
        print(value)

print("\nSEG file:", seg_path)
