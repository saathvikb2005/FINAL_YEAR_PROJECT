import pydicom
import numpy as np
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_048")
ct_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.212512542241432476118639218381"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
               "Modality", "") == "SEG"
)
seg = pydicom.dcmread(str(seg_path), force=True)
pixels = seg.pixel_array

ct_files = []
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT" and str(d.SeriesInstanceUID) == ct_uid:
            ct_files.append(d)
    except Exception:
        pass

ct_by_z = {round(float(d.ImagePositionPatient[2]), 3): d for d in ct_files}

shared = seg.SharedFunctionalGroupsSequence[0]
seg_iop = np.asarray(shared.PlaneOrientationSequence[0].ImageOrientationPatient, float)
seg_spacing = np.asarray(shared.PixelMeasuresSequence[0].PixelSpacing, float)

# DICOM: first IOP triplet is increasing column; second is increasing row.
seg_col_dir = seg_iop[:3]
seg_row_dir = seg_iop[3:]

print("Frame | Z(mm) | Pixels | Row offset range | Column offset range")
print("-" * 72)

for i, fg in enumerate(seg.PerFrameFunctionalGroupsSequence):
    segment_no = int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    if segment_no != 2:
        continue

    mask = pixels[i] > 0
    if not mask.any():
        continue

    ipp = np.asarray(fg.PlanePositionSequence[0].ImagePositionPatient, float)
    z = round(float(ipp[2]), 3)
    ct = ct_by_z.get(z)
    if ct is None:
        print(i + 1, z, "No exact Z-matched CT slice")
        continue

    ct_iop = np.asarray(ct.ImageOrientationPatient, float)
    ct_spacing = np.asarray(ct.PixelSpacing, float)
    ct_origin = np.asarray(ct.ImagePositionPatient, float)

    ct_col_dir = ct_iop[:3]
    ct_row_dir = ct_iop[3:]

    rr, cc = np.where(mask)
    points = [
        (int(rr.min()), int(cc.min())),
        (int(rr.min()), int(cc.max())),
        (int(rr.max()), int(cc.min())),
        (int(rr.max()), int(cc.max())),
        (int(np.median(rr)), int(np.median(cc))),
    ]

    row_offsets, col_offsets = [], []
    for r, c in points:
        physical = (
            ipp
            + c * seg_spacing[1] * seg_col_dir
            + r * seg_spacing[0] * seg_row_dir
        )
        delta = physical - ct_origin
        mapped_row = np.dot(delta, ct_row_dir) / ct_spacing[0]
        mapped_col = np.dot(delta, ct_col_dir) / ct_spacing[1]

        row_offsets.append(mapped_row - r)
        col_offsets.append(mapped_col - c)

    print(
        f"{i+1:5d} | {z:6.1f} | {int(mask.sum()):6d} | "
        f"{min(row_offsets):7.3f} to {max(row_offsets):7.3f} | "
        f"{min(col_offsets):7.3f} to {max(col_offsets):7.3f}"
    )
