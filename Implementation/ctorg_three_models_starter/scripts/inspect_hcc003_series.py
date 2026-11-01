import pydicom
from pathlib import Path

root = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC"
    r"\hcc_tace_seg\HCC_003"
)

for path in root.rglob("*.dcm"):
    try:
        ds = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True
        )
        if getattr(ds, "Modality", "") not in ("CT", "SEG"):
            continue

        print("\nFILE:", path)
        for key in [
            "Modality",
            "PatientID",
            "StudyInstanceUID",
            "SeriesInstanceUID",
            "FrameOfReferenceUID",
            "SeriesDescription",
            "ImageOrientationPatient",
            "PixelSpacing",
            "ImagePositionPatient",
            "NumberOfFrames",
        ]:
            if hasattr(ds, key):
                print("{}: {}".format(key, getattr(ds, key)))
    except Exception as e:
        print("READ ERROR:", path, str(e))
