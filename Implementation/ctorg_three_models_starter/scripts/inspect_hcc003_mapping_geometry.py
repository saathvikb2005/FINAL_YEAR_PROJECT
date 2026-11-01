import pydicom
import numpy as np
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_003")
target_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.281650679207816520863173918688"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True)

ct_files = []
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT" and getattr(d, "SeriesInstanceUID", "") == target_uid:
            ct_files.append((p, d))
    except Exception:
        pass

if not ct_files:
    raise SystemExit("Target AP CT series not found.")

ct_files.sort(key=lambda item: float(item[1].ImagePositionPatient[2]))
ct = ct_files[len(ct_files) // 2][1]

def show_ct(name, d):
    print(f"\n{name}")
    print("Series UID:", d.SeriesInstanceUID)
    print("Frame of Reference UID:", getattr(d, "FrameOfReferenceUID", "N/A"))
    print("Image Position Patient:", np.round(np.asarray(d.ImagePositionPatient, float), 5).tolist())
    print("Image Orientation:", np.round(np.asarray(d.ImageOrientationPatient, float), 5).tolist())
    print("Pixel Spacing:", np.round(np.asarray(d.PixelSpacing, float), 5).tolist())
    print("Rows, Columns:", d.Rows, d.Columns)

print("SEG:", seg_path)
print("\nSEG Frame of Reference UID:", getattr(seg, "FrameOfReferenceUID", "N/A"))
print("SEG Series UID:", seg.SeriesInstanceUID)

for frame_no in [9, 104, 199, 294, 30, 125, 220, 315, 50, 145, 240, 335]:
    fg = seg.PerFrameFunctionalGroupsSequence[frame_no - 1]
    pos = fg.PlanePositionSequence[0].ImagePositionPatient

    # Orientation and pixel measures may be per-frame or shared.
    ori_seq = getattr(fg, "PlaneOrientationSequence", None)
    if ori_seq:
        ori = ori_seq[0].ImageOrientationPatient
    else:
        shared = seg.SharedFunctionalGroupsSequence[0]
        ori = shared.PlaneOrientationSequence[0].ImageOrientationPatient

    pm_seq = getattr(fg, "PixelMeasuresSequence", None)
    if pm_seq:
        spacing = pm_seq[0].PixelSpacing
    else:
        shared = seg.SharedFunctionalGroupsSequence[0]
        spacing = shared.PixelMeasuresSequence[0].PixelSpacing

    print(
        f"\nSEG frame {frame_no}: "
        f"IPP={np.round(np.asarray(pos, float), 5).tolist()}, "
        f"IOP={np.round(np.asarray(ori, float), 5).tolist()}, "
        f"spacing={np.round(np.asarray(spacing, float), 5).tolist()}"
    )

show_ct("Middle slice of AP CT series", ct)
print("\nAP CT slice count:", len(ct_files))
