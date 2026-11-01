from pathlib import Path
import numpy as np
import pydicom
import matplotlib.pyplot as plt
import csv

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
BASE_OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc048_candidate_comparison")

SEG_PATH = ROOT / (
    r"HCC_048\1.3.6.1.4.1.14519.5.2.1.1706.8374.191238202133507320458118565112"
    r"\1.3.6.1.4.1.14519.5.2.1.1706.8374.299766419358710200971072115544"
    r"\08c174be-7d19-474b-a435-0d4188681342.dcm"
)

CANDIDATES = {
    "recon3_liver_phase": "1.3.6.1.4.1.14519.5.2.1.1706.8374.212512542241432476118639218381",
    "recon2_pre_liver": "1.3.6.1.4.1.14519.5.2.1.1706.8374.288936153358575768332977262270",
}

BASE_OUT.mkdir(parents=True, exist_ok=True)
seg = pydicom.dcmread(str(SEG_PATH))
seg_pixels = seg.pixel_array
frames = seg.PerFrameFunctionalGroupsSequence
shared = seg.SharedFunctionalGroupsSequence[0]

seg_spacing = np.array([float(v) for v in shared.PixelMeasuresSequence[0].PixelSpacing])
seg_iop = np.array([float(v) for v in shared.PlaneOrientationSequence[0].ImageOrientationPatient])
seg_col_dir, seg_row_dir = seg_iop[:3], seg_iop[3:]

tumor_frames = []
for i, fg in enumerate(frames):
    ids = getattr(fg, "SegmentIdentificationSequence", [])
    if not ids or int(ids[0].ReferencedSegmentNumber) != 2:
        continue
    mask = seg_pixels[i].astype(bool)
    if not np.any(mask):
        continue
    origin = np.array([float(v) for v in fg.PlanePositionSequence[0].ImagePositionPatient])
    tumor_frames.append((i + 1, origin, mask))

print("Tumor-positive SEG frames:", len(tumor_frames))

rows_out = []

for candidate_name, ct_uid in CANDIDATES.items():
    out_dir = BASE_OUT / candidate_name
    out_dir.mkdir(parents=True, exist_ok=True)

    ct_items = []
    for path in ROOT.joinpath("HCC_048").rglob("*.dcm"):
        try:
            hdr = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
            if str(getattr(hdr, "SeriesInstanceUID", "")) == ct_uid:
                ct_items.append((path, hdr))
        except Exception:
            pass

    if not ct_items:
        print(f"{candidate_name}: CT series not found")
        continue

    ct_items.sort(key=lambda item: float(item[1].ImagePositionPatient[2]))
    print(f"\n{candidate_name}: {len(ct_items)} CT slices")

    for frame_no, seg_origin, mask in tumor_frames:
        # Select the nearest CT plane using the physical plane normal.
        best = None
        for ct_path, hdr in ct_items:
            iop = np.array([float(v) for v in hdr.ImageOrientationPatient])
            col_dir, row_dir = iop[:3], iop[3:]
            normal = np.cross(col_dir, row_dir)
            normal /= np.linalg.norm(normal)
            ct_origin = np.array([float(v) for v in hdr.ImagePositionPatient])
            distance = abs(float(np.dot(seg_origin - ct_origin, normal)))
            if best is None or distance < best[0]:
                best = (distance, ct_path, hdr, col_dir, row_dir)

        distance, ct_path, hdr, ct_col_dir, ct_row_dir = best
        ct = pydicom.dcmread(str(ct_path))
        ct_img = ct.pixel_array.astype(np.float32)
        ct_img = ct_img * float(getattr(ct, "RescaleSlope", 1)) + float(getattr(ct, "RescaleIntercept", 0))

        ct_spacing = np.array([float(v) for v in ct.PixelSpacing])
        ct_origin = np.array([float(v) for v in ct.ImagePositionPatient])

        rr, cc = np.where(mask)
        xyz = (
            seg_origin
            + rr[:, None] * seg_spacing[0] * seg_row_dir
            + cc[:, None] * seg_spacing[1] * seg_col_dir
        )

        delta = xyz - ct_origin
        ct_rows = np.rint(np.sum(delta * ct_row_dir, axis=1) / ct_spacing[0]).astype(int)
        ct_cols = np.rint(np.sum(delta * ct_col_dir, axis=1) / ct_spacing[1]).astype(int)

        valid = (
            (ct_rows >= 0) & (ct_rows < ct_img.shape[0])
            & (ct_cols >= 0) & (ct_cols < ct_img.shape[1])
        )

        mapped = np.zeros(ct_img.shape, dtype=bool)
        mapped[ct_rows[valid], ct_cols[valid]] = True

        z = float(seg_origin[2])
        out_path = out_dir / f"HCC_048_mass_z_{z:.2f}.png"

        fig, ax = plt.subplots(figsize=(8, 8))
        ax.imshow(ct_img, cmap="gray", vmin=-150, vmax=250)
        if np.any(mapped):
            ax.contour(mapped.astype(np.uint8), levels=[0.5], colors=["magenta"], linewidths=1.0)
        ax.set_title(
            f"HCC_048 | {candidate_name}\nSEG Z={z:.2f} mm | plane distance={distance:.3f} mm"
        )
        ax.axis("off")
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        pct = 100.0 * valid.sum() / max(len(valid), 1)
        rows_out.append({
            "candidate": candidate_name,
            "seg_frame": frame_no,
            "seg_z_mm": z,
            "ct_z_mm": float(ct_origin[2]),
            "plane_distance_mm": distance,
            "mask_pixels": len(rr),
            "mapped_inside_pixels": int(valid.sum()),
            "inside_percent": pct,
            "overlay_path": str(out_path),
        })
        print(
            f"Frame {frame_no} | SEG Z={z:.2f} | CT Z={ct_origin[2]:.2f} "
            f"| plane distance={distance:.3f} mm | inside={pct:.1f}%"
        )

csv_path = BASE_OUT / "comparison_summary.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()) if rows_out else [])
    if rows_out:
        writer.writeheader()
        writer.writerows(rows_out)

print(f"\nSummary CSV: {csv_path}")
print(f"Comparison folder: {BASE_OUT}")
