import pydicom
from pathlib import Path

root = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC"
    r"\hcc_tace_seg\HCC_048"
)
uid = (
    "1.3.6.1.4.1.14519.5.2.1.1706.8374."
    "212512542241432476118639218381"
)

for path in root.rglob("*.dcm"):
    try:
        header = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True
        )
        if (
            str(getattr(header, "SeriesInstanceUID", "")) == uid
            and hasattr(header, "ImagePositionPatient")
        ):
            ds = header
            break
    except Exception:
        continue
else:
    raise RuntimeError("Selected CT series not found.")

print("CT path:", path)
for key in [
    "PatientID",
    "StudyInstanceUID",
    "SeriesInstanceUID",
    "FrameOfReferenceUID",
    "SeriesDescription",
    "StudyDate",
    "SeriesDate",
    "Modality",
    "ImageOrientationPatient",
    "PixelSpacing",
    "ImagePositionPatient",
    "SOPInstanceUID",
]:
    print("{}: {}".format(key, getattr(ds, key, "MISSING")))
