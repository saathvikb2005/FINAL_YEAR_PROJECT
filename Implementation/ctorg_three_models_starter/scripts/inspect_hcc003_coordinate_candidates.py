import pydicom
import numpy as np
from pathlib import Path

root = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC"
    r"\hcc_tace_seg\HCC_003"
)

seg_path = next(
    p for p in root.rglob("*.dcm")
    if pydicom.dcmread(
        str(p), stop_before_pixels=True, force=True
    ).Modality == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True)

print("SEG Frame of Reference:", seg.FrameOfReferenceUID)
print("SEG series:", seg.SeriesInstanceUID)

shared = seg.SharedFunctionalGroupsSequence[0]
ori = np.array(
    shared.PlaneOrientationSequence[0].ImageOrientationPatient,
    dtype=float
)
spacing = np.array(
    shared.PixelMeasuresSequence[0].PixelSpacing,
    dtype=float
)
print("SEG orientation:", ori.tolist())
print("SEG pixel spacing:", spacing.tolist())

tumor_z = []
for frame in seg.PerFrameFunctionalGroupsSequence:
    seg_no = int(
        frame.SegmentIdentificationSequence[0].ReferencedSegmentNumber
    )
    if seg_no != 2:
        continue
    pos = np.array(
        frame.PlanePositionSequence[0].ImagePositionPatient,
        dtype=float
    )
    tumor_z.append(float(pos[2]))

print("Tumor segment frame count:", len(tumor_z))
print("Tumor frame Z range:", min(tumor_z), "to", max(tumor_z))
print("First 12 tumor frame Z values:", tumor_z[:12])

seen = set()
print("\nCT series candidates:")
for path in root.rglob("*.dcm"):
    try:
        ds = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True
        )
        if getattr(ds, "Modality", "") != "CT":
            continue
        uid = str(ds.SeriesInstanceUID)
        if uid in seen:
            continue
        seen.add(uid)

        print("\nDescription:", getattr(ds, "SeriesDescription", "MISSING"))
        print("Series UID:", uid)
        print("Frame of Reference:", getattr(ds, "FrameOfReferenceUID", "MISSING"))
        print("Image orientation:", getattr(ds, "ImageOrientationPatient", "MISSING"))
        print("Pixel spacing:", getattr(ds, "PixelSpacing", "MISSING"))
        print("Sample image origin:", getattr(ds, "ImagePositionPatient", "MISSING"))
    except Exception:
        continue
