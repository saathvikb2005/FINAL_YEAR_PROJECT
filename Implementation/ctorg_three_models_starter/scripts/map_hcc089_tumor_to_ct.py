from pathlib import Path
import pydicom
import numpy as np

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
SEG_PATH = ROOT / (
    r"HCC_089\1.3.6.1.4.1.14519.5.2.1.1706.8374.324511982524894820763579219177"
    r"\1.2.276.0.7230010.3.1.3.8323329.2303.1600929169.408163"
    r"\c25aaa91-f29d-4b21-899d-83da89c31303.dcm"
)
CT_SERIES = {
    "LIVER_2PHASE": "1.3.6.1.4.1.14519.5.2.1.1706.8374.183102785669372706818207745188",
    "PRE_LIVER": "1.3.6.1.4.1.14519.5.2.1.1706.8374.495445119370122224936467178504",
}

seg = pydicom.dcmread(str(SEG_PATH))
pixels = seg.pixel_array
frames = seg.PerFrameFunctionalGroupsSequence
shared = seg.SharedFunctionalGroupsSequence[0]
seg_spacing = np.array([float(x) for x in shared.PixelMeasuresSequence[0].PixelSpacing])
seg_iop = np.array([float(x) for x in shared.PlaneOrientationSequence[0].ImageOrientationPatient])
seg_row_dir, seg_col_dir = seg_iop[:3], seg_iop[3:]

ct_slices = {name: [] for name in CT_SERIES}
for path in ROOT.joinpath("HCC_089").rglob("*"):
    if not path.is_file():
        continue
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        uid = str(getattr(ds, "SeriesInstanceUID", ""))
        for name, target_uid in CT_SERIES.items():
            if uid == target_uid:
                ct_slices[name].append((path, ds))
    except Exception:
        continue

for name in CT_SERIES:
    ct_slices[name].sort(
        key=lambda x: float(x[1].ImagePositionPatient[2])
    )

tumor_frames = []
for i, fg in enumerate(frames):
    sid = getattr(fg, "SegmentIdentificationSequence", [])
    if not sid or int(sid[0].ReferencedSegmentNumber) != 2:
        continue
    mask = pixels[i]
    if not np.any(mask):
        continue
    pseq = getattr(fg, "PlanePositionSequence", [])
    if not pseq:
        continue
    origin = np.array([float(v) for v in pseq[0].ImagePositionPatient])
    rr, cc = np.where(mask > 0)
    tumor_frames.append((i + 1, origin, rr, cc, int(mask.sum())))

print("Tumor-positive frames:", len(tumor_frames))
print("SEG spacing:", seg_spacing.tolist())
print("SEG orientation:", seg_iop.tolist())

for name, series in ct_slices.items():
    print(f"\n===== {name}: {len(series)} CT slices =====")
    if not series:
        print("Series not found locally.")
        continue

    ct0 = series[0][1]
    ct_iop = np.array([float(x) for x in ct0.ImageOrientationPatient])
    row_dir, col_dir = ct_iop[:3], ct_iop[3:]
    spacing = np.array([float(x) for x in ct0.PixelSpacing])
    origin0 = np.array([float(x) for x in ct0.ImagePositionPatient])
    normal = np.cross(row_dir, col_dir)
    projections = [
        (float(np.dot(np.array(ds.ImagePositionPatient, dtype=float), normal)), path, ds)
        for path, ds in series
    ]

    print("CT FrameOfReferenceUID:", getattr(ct0, "FrameOfReferenceUID", ""))
    print("CT spacing:", spacing.tolist())
    print("CT orientation:", ct_iop.tolist())
    print("CT first origin:", origin0.tolist())

    for frame_no, seg_origin, rr, cc, npx in tumor_frames:
        # Physical coordinates of mask pixels in patient space
        sample_idx = np.linspace(0, len(rr) - 1, min(25, len(rr))).astype(int)
        xyz = (
            seg_origin
            + rr[sample_idx, None] * seg_spacing[0] * seg_row_dir
            + cc[sample_idx, None] * seg_spacing[1] * seg_col_dir
        )
        z_seg = float(seg_origin[2])
        nearest = min(projections, key=lambda item: abs(item[0] - z_seg))
        z_ct, ct_path, ct_ds = nearest
        ct_origin = np.array(ct_ds.ImagePositionPatient, dtype=float)
        delta = xyz - ct_origin
        ct_rows = np.sum(delta * row_dir, axis=1) / spacing[0]
        ct_cols = np.sum(delta * col_dir, axis=1) / spacing[1]
        inside = (
            (ct_rows >= 0) & (ct_rows < int(ct_ds.Rows))
            & (ct_cols >= 0) & (ct_cols < int(ct_ds.Columns))
        )
        print(
            f"Frame {frame_no:3d} z={z_seg:8.3f} px={npx:4d} | "
            f"nearest CT z={z_ct:8.3f} dz={abs(z_ct-z_seg):.3f} | "
            f"mapped row={ct_rows.min():.1f}..{ct_rows.max():.1f} "
            f"col={ct_cols.min():.1f}..{ct_cols.max():.1f} "
            f"inside={int(inside.sum())}/{len(inside)} sample points"
        )
