import pydicom
import numpy as np
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_003")
out = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\scripts")

target_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.281650679207816520863173918688"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
seg = pydicom.dcmread(str(seg_path))
seg_pixels = seg.pixel_array

ct_slices = []
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT" and getattr(d, "SeriesInstanceUID", "") == target_uid:
            ct_slices.append((p, d))
    except Exception:
        continue

ct_by_z = {}
for p, d in ct_slices:
    z = round(float(d.ImagePositionPatient[2]), 3)
    ct_by_z[z] = (p, d)

def seg_geometry(frame):
    fg = seg.PerFrameFunctionalGroupsSequence[frame]
    pos = np.asarray(fg.PlanePositionSequence[0].ImagePositionPatient, float)
    shared = seg.SharedFunctionalGroupsSequence[0]
    ori_seq = getattr(fg, "PlaneOrientationSequence", None)
    ori = np.asarray(
        ori_seq[0].ImageOrientationPatient if ori_seq
        else shared.PlaneOrientationSequence[0].ImageOrientationPatient,
        float
    )
    pm_seq = getattr(fg, "PixelMeasuresSequence", None)
    spacing = np.asarray(
        pm_seq[0].PixelSpacing if pm_seq
        else shared.PixelMeasuresSequence[0].PixelSpacing,
        float
    )
    return pos, ori, spacing

for frame_no in [104, 125, 145]:
    frame_idx = frame_no - 1
    mask = seg_pixels[frame_idx] > 0
    rr, cc = np.where(mask)

    pos, ori, sp = seg_geometry(frame_idx)
    z = round(float(pos[2]), 3)

    print(f"\nSEG frame {frame_no}, Z={z} mm")
    print("Tumor pixels:", len(rr))

    if z not in ct_by_z:
        print("No exact-Z CT slice found.")
        continue

    ct_path, ct = ct_by_z[z]
    ct_pos = np.asarray(ct.ImagePositionPatient, float)
    ct_ori = np.asarray(ct.ImageOrientationPatient, float)
    ct_sp = np.asarray(ct.PixelSpacing, float)

    # Transform tumor pixel coordinates into patient coordinates.
    xyz = (
        pos[None, :]
        + cc[:, None] * ori[:3][None, :] * sp[1]
        + rr[:, None] * ori[3:][None, :] * sp[0]
    )

    delta = xyz - ct_pos[None, :]
    ct_cols = delta @ ct_ori[:3] / ct_sp[1]
    ct_rows = delta @ ct_ori[3:] / ct_sp[0]

    print("CT file:", ct_path.name)
    print("CT Z:", float(ct_pos[2]))
    print("Mapped CT rows min/max:", round(ct_rows.min(), 2), round(ct_rows.max(), 2))
    print("Mapped CT cols min/max:", round(ct_cols.min(), 2), round(ct_cols.max(), 2))
    print("All mapped points inside CT bounds:",
          bool(np.all((ct_rows >= 0) & (ct_rows < ct.Rows) &
                      (ct_cols >= 0) & (ct_cols < ct.Columns))))
    print("SEG FoR UID equals CT FoR UID:",
          getattr(seg, "FrameOfReferenceUID", None) ==
          getattr(ct, "FrameOfReferenceUID", None))
