from pathlib import Path

import numpy as np
import pydicom
import matplotlib.pyplot as plt

ROOT = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg"
)
OUT = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
    r"\results\dataset_audit\hcc089_physical_overlays_all"
)
SEG_PATH = ROOT / (
    r"HCC_089\1.3.6.1.4.1.14519.5.2.1.1706.8374.324511982524894820763579219177"
    r"\1.2.276.0.7230010.3.1.3.8323329.2303.1600929169.408163"
    r"\c25aaa91-f29d-4b21-899d-83da89c31303.dcm"
)
CT_UID = (
    "1.3.6.1.4.1.14519.5.2.1.1706.8374."
    "183102785669372706818207745188"
)

OUT.mkdir(parents=True, exist_ok=True)

seg = pydicom.dcmread(str(SEG_PATH))
seg_pixels = seg.pixel_array
frames = seg.PerFrameFunctionalGroupsSequence
shared = seg.SharedFunctionalGroupsSequence[0]

seg_spacing = np.array([
    float(v)
    for v in shared.PixelMeasuresSequence[0].PixelSpacing
])
seg_iop = np.array([
    float(v)
    for v in shared.PlaneOrientationSequence[0].ImageOrientationPatient
])

# DICOM convention: first IOP vector = increasing columns;
# second IOP vector = increasing rows.
seg_col_dir = seg_iop[:3]
seg_row_dir = seg_iop[3:]

# Find all local CT slices in the selected series.
ct_items = []
for path in ROOT.joinpath("HCC_089").rglob("*"):
    if not path.is_file():
        continue
    try:
        hdr = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True
        )
        if (
            str(getattr(hdr, "SeriesInstanceUID", "")) == CT_UID
            and hasattr(hdr, "ImagePositionPatient")
            and hasattr(hdr, "ImageOrientationPatient")
        ):
            ct_items.append((path, hdr))
    except Exception:
        continue

if not ct_items:
    raise RuntimeError("Selected CT series not found locally.")

# Index CT slices by physical plane position.
ct_items.sort(
    key=lambda item: float(item[1].ImagePositionPatient[2])
)

# Collect every non-empty Mass frame.
tumor_frames = []
for i, fg in enumerate(frames):
    sid = getattr(fg, "SegmentIdentificationSequence", [])
    if not sid or int(sid[0].ReferencedSegmentNumber) != 2:
        continue

    pos_seq = getattr(fg, "PlanePositionSequence", [])
    if not pos_seq:
        continue

    mask = seg_pixels[i].astype(bool)
    if not np.any(mask):
        continue

    origin = np.array([
        float(v) for v in pos_seq[0].ImagePositionPatient
    ])
    tumor_frames.append((i, origin, mask))

# One representative frame per unique Z plane.
unique_frames = {}
for i, origin, mask in tumor_frames:
    key = round(float(origin[2]), 3)
    unique_frames.setdefault(key, (i, origin, mask))

print(f"Non-empty Mass frames: {len(tumor_frames)}")
print(f"Unique tumor-positive Z planes: {len(unique_frames)}")
print(f"CT slices in selected series: {len(ct_items)}")

summary = []

for z, (frame_idx, seg_origin, mask) in sorted(unique_frames.items()):
    # Find nearest CT plane using its physical plane normal.
    best = None
    for ct_path, ct_hdr in ct_items:
        ct_iop = np.array([
            float(v) for v in ct_hdr.ImageOrientationPatient
        ])
        ct_col_dir = ct_iop[:3]
        ct_row_dir = ct_iop[3:]
        normal = np.cross(ct_col_dir, ct_row_dir)
        normal /= np.linalg.norm(normal)

        ct_origin = np.array([
            float(v) for v in ct_hdr.ImagePositionPatient
        ])
        distance = abs(float(np.dot(seg_origin - ct_origin, normal)))

        if best is None or distance < best[0]:
            best = (
                distance, ct_path, ct_hdr,
                ct_col_dir, ct_row_dir, normal
            )

    distance, ct_path, ct_hdr, ct_col_dir, ct_row_dir, normal = best

    # Read the chosen CT image and convert to HU.
    ct = pydicom.dcmread(str(ct_path))
    ct_pixels = ct.pixel_array.astype(np.float32)
    ct_pixels = (
        ct_pixels * float(getattr(ct, "RescaleSlope", 1))
        + float(getattr(ct, "RescaleIntercept", 0))
    )

    ct_spacing = np.array([
        float(v) for v in ct.PixelSpacing
    ])
    ct_origin = np.array([
        float(v) for v in ct.ImagePositionPatient
    ])

    # Convert every SEG mask pixel to patient-space coordinates.
    rr, cc = np.where(mask)
    xyz = (
        seg_origin
        + rr[:, None] * seg_spacing[0] * seg_row_dir
        + cc[:, None] * seg_spacing[1] * seg_col_dir
    )

    # Project patient-space points onto the CT pixel grid.
    delta = xyz - ct_origin
    ct_rows = np.rint(
        np.sum(delta * ct_row_dir, axis=1) / ct_spacing[0]
    ).astype(int)
    ct_cols = np.rint(
        np.sum(delta * ct_col_dir, axis=1) / ct_spacing[1]
    ).astype(int)

    valid = (
        (ct_rows >= 0) & (ct_rows < ct_pixels.shape[0])
        & (ct_cols >= 0) & (ct_cols < ct_pixels.shape[1])
    )

    mapped = np.zeros(ct_pixels.shape, dtype=bool)
    mapped[ct_rows[valid], ct_cols[valid]] = True

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(ct_pixels, cmap="gray", vmin=-150, vmax=250)
    if np.any(mapped):
        ax.contour(mapped.astype(np.uint8), levels=[0.5],
                   colors=["magenta"], linewidths=1.0)

    ax.set_title(
        f"HCC_089 | Mass SEG | SEG Z={z:.2f} mm\n"
        f"CT plane distance={distance:.3f} mm"
    )
    ax.axis("off")

    out_path = OUT / f"HCC_089_mass_z_{z:.2f}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    inside_pct = 100.0 * valid.sum() / max(len(valid), 1)
    summary.append((z, distance, len(rr), int(valid.sum()), inside_pct))

    print(
        f"Z={z:8.2f} | plane distance={distance:.3f} mm"
        f" | pixels={len(rr)} | inside={valid.sum()}/{len(valid)}"
        f" ({inside_pct:.1f}%) | {out_path.name}"
    )

# Save a simple audit summary.
report = OUT / "overlay_summary.csv"
with report.open("w", encoding="utf-8") as f:
    f.write("SEG_Z_mm,CT_plane_distance_mm,SEG_pixels,"
            "mapped_inside_pixels,inside_percent\n")
    for row in summary:
        f.write(
            f"{row[0]:.3f},{row[1]:.4f},{row[2]},"
            f"{row[3]},{row[4]:.2f}\n"
        )

print(f"\nSaved {len(summary)} overlays.")
print(f"Summary CSV: {report}")
print(f"Output folder: {OUT}")