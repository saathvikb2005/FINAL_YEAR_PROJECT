from pathlib import Path
import numpy as np
import pydicom
import matplotlib.pyplot as plt

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_048")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc048_offset_diagnostic")
SEG_NAME = "08c174be-7d19-474b-a435-0d4188681342.dcm"
CT_UID = "1.3.6.1.4.1.14519.5.2.1.1706.8374.212512542241432476118639218381"
TARGET_Z = -248.5

OUT.mkdir(parents=True, exist_ok=True)
seg_path = next(ROOT.rglob(SEG_NAME))
seg = pydicom.dcmread(str(seg_path))
pixels = seg.pixel_array
frames = seg.PerFrameFunctionalGroupsSequence
shared = seg.SharedFunctionalGroupsSequence[0]

spacing = np.array(shared.PixelMeasuresSequence[0].PixelSpacing, float)
iop = np.array(shared.PlaneOrientationSequence[0].ImageOrientationPatient, float)
col_dir, row_dir = iop[:3], iop[3:]

frame_idx = None
for i, fg in enumerate(frames):
    ids = getattr(fg, "SegmentIdentificationSequence", [])
    if not ids or int(ids[0].ReferencedSegmentNumber) != 2:
        continue
    z = float(fg.PlanePositionSequence[0].ImagePositionPatient[2])
    if np.isclose(z, TARGET_Z, atol=0.001) and np.any(pixels[i]):
        frame_idx = i
        break

if frame_idx is None:
    raise RuntimeError(f"No non-empty tumor SEG frame found at Z={TARGET_Z}")

fg = frames[frame_idx]
mask = pixels[frame_idx].astype(bool)
origin = np.array(fg.PlanePositionSequence[0].ImagePositionPatient, float)
rr, cc = np.where(mask)
xyz = origin + rr[:, None] * spacing[0] * row_dir + cc[:, None] * spacing[1] * col_dir

ct_path = None
for p in ROOT.rglob("*.dcm"):
    try:
        h = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if str(getattr(h, "SeriesInstanceUID", "")) == CT_UID and hasattr(h, "ImagePositionPatient"):
            if np.isclose(float(h.ImagePositionPatient[2]), TARGET_Z, atol=0.001):
                ct_path = p
                break
    except Exception:
        pass

if ct_path is None:
    raise RuntimeError(f"No exact-Z CT slice found at Z={TARGET_Z}")

ct = pydicom.dcmread(str(ct_path))
image = ct.pixel_array.astype(np.float32)
image = image * float(getattr(ct, "RescaleSlope", 1)) + float(getattr(ct, "RescaleIntercept", 0))

ct_iop = np.array(ct.ImageOrientationPatient, float)
ct_col_dir, ct_row_dir = ct_iop[:3], ct_iop[3:]
ct_spacing = np.array(ct.PixelSpacing, float)
ct_origin = np.array(ct.ImagePositionPatient, float)
delta = xyz - ct_origin

rows = np.rint(delta @ ct_row_dir / ct_spacing[0]).astype(int)
cols = np.rint(delta @ ct_col_dir / ct_spacing[1]).astype(int)
valid = ((rows >= 0) & (rows < image.shape[0]) & (cols >= 0) & (cols < image.shape[1]))

print(f"SEG frame: {frame_idx + 1}, Z={TARGET_Z}, tumor pixels={len(rr)}")
print(f"CT series: {CT_UID}")
print(f"All mapped pixels inside CT: {valid.sum()}/{len(valid)}")
print(f"SEG Frame of Reference matches CT: {getattr(seg, 'FrameOfReferenceUID', '') == getattr(ct, 'FrameOfReferenceUID', '')}")
print("Diagnostic shifts are in CT pixel coordinates (row, column).")

# Compare unshifted mapping with one-pixel shifts; these are diagnostics, not corrections.
variants = [
    ("physical_mapping", 0, 0),
    ("shift_row_plus1", 1, 0),
    ("shift_row_minus1", -1, 0),
    ("shift_col_plus1", 0, 1),
    ("shift_col_minus1", 0, -1),
]

fig, axes = plt.subplots(1, 5, figsize=(22, 5))
for ax, (name, dr, dc) in zip(axes, variants):
    r = rows + dr
    c = cols + dc
    ok = ((r >= 0) & (r < image.shape[0]) & (c >= 0) & (c < image.shape[1]))
    mapped = np.zeros(image.shape, dtype=bool)
    mapped[r[ok], c[ok]] = True

    ax.imshow(image, cmap="gray", vmin=-150, vmax=250)
    if mapped.any():
        ax.contour(mapped.astype(np.uint8), levels=[0.5], colors=["magenta"], linewidths=1.1)
    ax.set_title(name.replace("_", "\n"), fontsize=9)
    ax.axis("off")

fig.suptitle("HCC_048 | SEG-to-CT coordinate diagnostic | Z=-248.50 mm")
fig.tight_layout()
out_path = OUT / "HCC_048_offset_diagnostic_z_-248.50.png"
fig.savefig(out_path, dpi=160, bbox_inches="tight")
plt.close(fig)

print("Saved diagnostic:", out_path)
