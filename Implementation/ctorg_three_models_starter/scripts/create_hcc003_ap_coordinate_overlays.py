import pydicom
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from collections import defaultdict

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_003")
out = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc003_ap_coordinate_overlays")
out.mkdir(parents=True, exist_ok=True)

seg_path = next(
    p for p in base.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
seg = pydicom.dcmread(str(seg_path))
seg_pixels = seg.pixel_array
shared = seg.SharedFunctionalGroupsSequence[0]
seg_ori = np.asarray(shared.PlaneOrientationSequence[0].ImageOrientationPatient, float)
seg_spacing = np.asarray(shared.PixelMeasuresSequence[0].PixelSpacing, float)

# Locate the AP series and index its CT slices by patient-space Z.
target_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.281650679207816520863173918688"
ct_by_z = {}
ct_geom = None

for p in base.rglob("*.dcm"):
    try:
        h = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(h, "Modality", "") != "CT" or str(h.SeriesInstanceUID) != target_uid:
            continue
        z = round(float(h.ImagePositionPatient[2]), 3)
        ct_by_z[z] = p
        if ct_geom is None:
            ct_geom = (
                np.asarray(h.ImageOrientationPatient, float),
                np.asarray(h.PixelSpacing, float)
            )
    except Exception:
        continue

if not ct_by_z:
    raise RuntimeError("AP CT series not found.")

ct_ori, ct_spacing = ct_geom
rows_out = []

for i, frame in enumerate(seg.PerFrameFunctionalGroupsSequence):
    seg_no = int(frame.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    if seg_no != 2:
        continue

    mask = seg_pixels[i] > 0
    if not mask.any():
        continue

    seg_origin = np.asarray(frame.PlanePositionSequence[0].ImagePositionPatient, float)
    z = round(float(seg_origin[2]), 3)

    if z not in ct_by_z:
        rows_out.append((i + 1, z, int(mask.sum()), "NO_EXACT_Z_MATCH", 0))
        continue

    ct_path = ct_by_z[z]
    ct = pydicom.dcmread(str(ct_path))
    ct_origin = np.asarray(ct.ImagePositionPatient, float)

    rr, cc = np.where(mask)
    xyz = (
        seg_origin[None, :]
        + cc[:, None] * seg_ori[:3][None, :] * seg_spacing[1]
        + rr[:, None] * seg_ori[3:][None, :] * seg_spacing[0]
    )
    delta = xyz - ct_origin[None, :]
    ct_cols = delta @ ct_ori[:3] / ct_spacing[1]
    ct_rows = delta @ ct_ori[3:] / ct_spacing[0]

    # Only use pixels whose mapped positions land close to CT pixel centers.
    rounded_r = np.rint(ct_rows).astype(int)
    rounded_c = np.rint(ct_cols).astype(int)
    inside = (
        (rounded_r >= 0) & (rounded_r < ct.Rows) &
        (rounded_c >= 0) & (rounded_c < ct.Columns)
    )
    mapped = np.zeros((ct.Rows, ct.Columns), dtype=bool)
    mapped[rounded_r[inside], rounded_c[inside]] = True

    if inside.any():
        image = ct.pixel_array.astype(np.float32)
        slope = float(getattr(ct, "RescaleSlope", 1))
        intercept = float(getattr(ct, "RescaleIntercept", 0))
        image = image * slope + intercept
        image = np.clip(image, -150, 250)

        fig, ax = plt.subplots(figsize=(7, 7))
        ax.imshow(image, cmap="gray", vmin=-150, vmax=250)
        ax.contour(mapped.astype(np.uint8), levels=[0.5], linewidths=0.8)
        ax.set_title("HCC_003 | SEG frame {} | Z={:.2f} mm".format(i + 1, z))
        ax.axis("off")
        fig.tight_layout()
        image_path = out / "frame_{:03d}_z_{:.2f}.png".format(i + 1, z)
        fig.savefig(image_path, dpi=130)
        plt.close(fig)

    rows_out.append((
        i + 1, z, int(mask.sum()),
        "EXACT_Z_MATCH",
        int(inside.sum())
    ))

summary = out / "overlay_summary.csv"
with summary.open("w", encoding="utf-8") as f:
    f.write("seg_frame,z_mm,tumor_pixels,status,pixels_inside_ct\n")
    for row in rows_out:
        f.write("{},{},{},{},{}\n".format(*row))

print("Overlay folder:", out)
print("Tumor-positive frames processed:", len(rows_out))
print("Exact Z matches:", sum(r[3] == "EXACT_Z_MATCH" for r in rows_out))
print("Summary CSV:", summary)
for row in rows_out[:12]:
    print(row)
