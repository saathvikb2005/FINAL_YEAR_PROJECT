from pathlib import Path
import numpy as np
import pydicom
import matplotlib.pyplot as plt

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc048_physical_overlays")
SEG_PATH = ROOT / (
    r"HCC_048\1.3.6.1.4.1.14519.5.2.1.1706.8374.191238202133507320458118565112"
    r"\1.3.6.1.4.1.14519.5.2.1.1706.8374.299766419358710200971072115544"
    r"\08c174be-7d19-474b-a435-0d4188681342.dcm"
)
CT_UID = "1.3.6.1.4.1.14519.5.2.1.1706.8374.288936153358575768332977262270"

OUT.mkdir(parents=True, exist_ok=True)
seg = pydicom.dcmread(str(SEG_PATH))
seg_pixels = seg.pixel_array
frames = seg.PerFrameFunctionalGroupsSequence
shared = seg.SharedFunctionalGroupsSequence[0]

spacing = np.array([float(v) for v in shared.PixelMeasuresSequence[0].PixelSpacing])
iop = np.array([float(v) for v in shared.PlaneOrientationSequence[0].ImageOrientationPatient])
col_dir, row_dir = iop[:3], iop[3:]

ct_items = []
for path in ROOT.joinpath("HCC_048").rglob("*.dcm"):
    try:
        hdr = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        if str(getattr(hdr, "SeriesInstanceUID", "")) == CT_UID:
            ct_items.append((path, hdr))
    except Exception:
        pass

if not ct_items:
    raise RuntimeError("Selected CT series not found.")

ct_items.sort(key=lambda item: float(item[1].ImagePositionPatient[2]))
ct_by_z = {round(float(h.ImagePositionPatient[2]), 3): (p, h) for p, h in ct_items}

count = 0
for i, fg in enumerate(frames):
    ids = getattr(fg, "SegmentIdentificationSequence", [])
    if not ids or int(ids[0].ReferencedSegmentNumber) != 2:
        continue

    mask = seg_pixels[i].astype(bool)
    if not np.any(mask):
        continue

    origin = np.array([float(v) for v in fg.PlanePositionSequence[0].ImagePositionPatient])
    z = round(float(origin[2]), 3)

    if z not in ct_by_z:
        print(f"No exact-Z CT slice for SEG frame {i+1}, Z={z}")
        continue

    ct_path, ct_hdr = ct_by_z[z]
    ct = pydicom.dcmread(str(ct_path))
    ct_pixels = ct.pixel_array.astype(np.float32)
    ct_pixels = ct_pixels * float(getattr(ct, "RescaleSlope", 1)) + float(getattr(ct, "RescaleIntercept", 0))

    rr, cc = np.where(mask)
    xyz = (
        origin
        + rr[:, None] * spacing[0] * row_dir
        + cc[:, None] * spacing[1] * col_dir
    )

    ct_iop = np.array([float(v) for v in ct.ImageOrientationPatient])
    ct_col_dir, ct_row_dir = ct_iop[:3], ct_iop[3:]
    ct_spacing = np.array([float(v) for v in ct.PixelSpacing])
    ct_origin = np.array([float(v) for v in ct.ImagePositionPatient])
    delta = xyz - ct_origin

    rows = np.rint(np.sum(delta * ct_row_dir, axis=1) / ct_spacing[0]).astype(int)
    cols = np.rint(np.sum(delta * ct_col_dir, axis=1) / ct_spacing[1]).astype(int)
    valid = (
        (rows >= 0) & (rows < ct_pixels.shape[0]) &
        (cols >= 0) & (cols < ct_pixels.shape[1])
    )

    mapped = np.zeros(ct_pixels.shape, dtype=bool)
    mapped[rows[valid], cols[valid]] = True

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(ct_pixels, cmap="gray", vmin=-150, vmax=250)
    if np.any(mapped):
        ax.contour(mapped.astype(np.uint8), levels=[0.5], colors=["magenta"], linewidths=1.0)
    ax.set_title(f"HCC_048 | Mass SEG | Z={z:.2f} mm")
    ax.axis("off")

    out_path = OUT / f"HCC_048_mass_z_{z:.2f}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    pct = 100.0 * valid.sum() / max(len(valid), 1)
    print(f"Frame {i+1} | Z={z:.2f} | pixels={len(rr)} | inside={valid.sum()}/{len(valid)} ({pct:.1f}%)")
    print(f"Saved: {out_path}")
    count += 1

print(f"\nGenerated overlays: {count}")
print(f"Output folder: {OUT}")
