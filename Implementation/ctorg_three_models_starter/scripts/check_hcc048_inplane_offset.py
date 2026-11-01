import pydicom
import numpy as np
from pathlib import Path

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_048")
seg_path = next(root.rglob("08c174be-7d19-474b-a435-0d4188681342.dcm"))
ct_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.212512542241432476118639218381"

seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True)
shared = seg.SharedFunctionalGroupsSequence[0]
seg_iop = np.array(shared.PlaneOrientationSequence[0].ImageOrientationPatient, float)
seg_spacing = np.array(shared.PixelMeasuresSequence[0].PixelSpacing, float)

ct_path = None
for path in root.rglob("*.dcm"):
    ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
    if str(getattr(ds, "SeriesInstanceUID", "")) == ct_uid and hasattr(ds, "ImagePositionPatient"):
        ct_path = path
        break

if ct_path is None:
    raise RuntimeError("Could not locate the selected CT series.")

ct = pydicom.dcmread(str(ct_path), stop_before_pixels=True, force=True)
ct_iop = np.array(ct.ImageOrientationPatient, float)
ct_spacing = np.array(ct.PixelSpacing, float)

print("SEG spacing:", seg_spacing)
print("CT spacing: ", ct_spacing)
print("SEG orientation:", seg_iop)
print("CT orientation: ", ct_iop)
print("Orientation matches:", np.allclose(seg_iop, ct_iop, atol=1e-4))
print("Spacing matches:", np.allclose(seg_spacing, ct_spacing, atol=1e-4))
print("SEG Frame of Reference:", getattr(seg, "FrameOfReferenceUID", "MISSING"))
print("CT Frame of Reference: ", getattr(ct, "FrameOfReferenceUID", "MISSING"))

for frame_no in [144, 147, 149, 151]:
    fg = seg.PerFrameFunctionalGroupsSequence[frame_no - 1]
    seg_origin = np.array(fg.PlanePositionSequence[0].ImagePositionPatient, float)
    ct_origin = np.array(ct.ImagePositionPatient, float)

    delta = seg_origin - ct_origin
    row_offset = np.dot(delta, ct_iop[3:]) / ct_spacing[0]
    col_offset = np.dot(delta, ct_iop[:3]) / ct_spacing[1]

    print(
        f"Frame {frame_no}: SEG origin={np.round(seg_origin, 4)}, "
        f"CT sample origin={np.round(ct_origin, 4)}, "
        f"origin delta mm={np.round(delta, 4)}, "
        f"projected row/col offset px=({row_offset:.3f}, {col_offset:.3f})"
    )
