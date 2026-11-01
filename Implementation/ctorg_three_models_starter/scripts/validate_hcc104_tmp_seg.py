from pathlib import Path
import pydicom

path = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg\hcc_tace_seg"
    r"\HCC_104\2006-07-02-CT  CAP  LIVER-77724"
    r"\300-Segmentation-62477"
    r"\a66f45aa-d120-4ea6-8965-7b137bbde416.dcm.tmp"
)

print("=== FILE CHECK ===")
print("Exists:", path.exists())
if not path.exists():
    raise SystemExit("Target file not found.")

print("Size in bytes:", path.stat().st_size)

print("\n=== DICOM METADATA ===")
ds = pydicom.dcmread(str(path), force=True)

for tag in [
    "SOPClassUID", "SOPInstanceUID", "Modality", "PatientID",
    "StudyInstanceUID", "SeriesInstanceUID", "SeriesDescription",
    "Rows", "Columns", "NumberOfFrames", "TransferSyntaxUID"
]:
    value = ds.get(tag, "<missing>")
    print(f"{tag}: {value}")

print("\n=== SEGMENT DEFINITIONS ===")
for item in getattr(ds, "SegmentSequence", []):
    print({
        "number": getattr(item, "SegmentNumber", None),
        "label": getattr(item, "SegmentLabel", None),
        "algorithm": getattr(item, "SegmentAlgorithmType", None),
        "description": getattr(item, "SegmentDescription", None),
    })

print("\n=== REFERENCED SERIES ===")
found = set()

def walk(dataset):
    for element in dataset:
        if element.keyword == "SeriesInstanceUID":
            value = str(element.value).strip()
            if value:
                found.add(value)
        if element.VR == "SQ":
            for child in element.value:
                walk(child)

walk(ds)
print("Referenced/contained SeriesInstanceUID values:")
for uid in sorted(found):
    print(uid)

print("\n=== PIXEL DATA DECODE ===")
try:
    pixels = ds.pixel_array
    print("Decode successful")
    print("Pixel array shape:", pixels.shape)
    print("Pixel dtype:", pixels.dtype)
    print("Unique values (first 20):", __import__("numpy").unique(pixels)[:20])
    print("Nonzero pixel count:", int((pixels != 0).sum()))
except Exception as exc:
    print("Decode failed:", type(exc).__name__, str(exc))

print("\n=== END ===")
