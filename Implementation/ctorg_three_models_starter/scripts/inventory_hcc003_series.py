import pydicom
from pathlib import Path

root = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC"
    r"\hcc_tace_seg\HCC_003"
)
series = {}

for path in root.rglob("*.dcm"):
    try:
        ds = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True
        )
        uid = getattr(ds, "SeriesInstanceUID", None)
        modality = getattr(ds, "Modality", "")
        if not uid or modality not in ("CT", "SEG"):
            continue

        if uid not in series:
            series[uid] = {
                "modality": modality,
                "description": getattr(ds, "SeriesDescription", "MISSING"),
                "study": getattr(ds, "StudyInstanceUID", "MISSING"),
                "for_uid": getattr(ds, "FrameOfReferenceUID", "MISSING"),
                "orientation": str(getattr(ds, "ImageOrientationPatient", "MISSING")),
                "spacing": str(getattr(ds, "PixelSpacing", "MISSING")),
                "count": 0,
                "z": [],
            }

        item = series[uid]
        item["count"] += 1
        pos = getattr(ds, "ImagePositionPatient", None)
        if pos is not None and len(pos) >= 3:
            item["z"].append(float(pos[2]))
    except Exception:
        continue

for uid, item in series.items():
    z = item["z"]
    zrange = (
        "{:.2f} to {:.2f}".format(min(z), max(z))
        if z else "not available"
    )
    print("\nModality:", item["modality"])
    print("Description:", item["description"])
    print("Series UID:", uid)
    print("Frame of Reference:", item["for_uid"])
    print("Images/frames counted:", item["count"])
    print("Z range:", zrange)
    print("Orientation:", item["orientation"])
    print("Pixel spacing:", item["spacing"])
