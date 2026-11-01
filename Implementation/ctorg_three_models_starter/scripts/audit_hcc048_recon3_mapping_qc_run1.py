from pathlib import Path
import csv
import numpy as np
import pydicom
import matplotlib.pyplot as plt

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc048_recon3_mapping_qc_run1")
SEG_PATH = ROOT / (
    r"HCC_048\1.3.6.1.4.1.14519.5.2.1.1706.8374.191238202133507320458118565112"
    r"\1.3.6.1.4.1.14519.5.2.1.1706.8374.299766419358710200971072115544"
    r"\08c174be-7d19-474b-a435-0d4188681342.dcm"
)
CT_UID = "1.3.6.1.4.1.14519.5.2.1.1706.8374.212512542241432476118639218381"

if OUT.exists() and any(OUT.iterdir()):
    raise RuntimeError(f"Output folder is not empty; refusing to overwrite: {OUT}")
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
        if str(getattr(hdr, "Modality", "")).upper() == "CT" and str(getattr(hdr, "SeriesInstanceUID", "")) == CT_UID:
            ct_items.append((path, hdr))
    except Exception:
        pass

if not ct_items:
    raise RuntimeError("Study A Recon 3 CT series not found.")

ct_by_z = {}
for path, hdr in ct_items:
    z = round(float(hdr.ImagePositionPatient[2]), 4)
    if z in ct_by_z:
        raise RuntimeError(f"Duplicate CT Z coordinate detected: {z}")
    ct_by_z[z] = (path, hdr)

rows_out = []
nonempty_count = 0
exact_z_count = 0

for i, fg in enumerate(frames):
    ids = getattr(fg, "SegmentIdentificationSequence", [])
    if not ids or int(ids[0].ReferencedSegmentNumber) != 2:
        continue

    mask = seg_pixels[i].astype(bool)
    pixel_count = int(mask.sum())
    if pixel_count == 0:
        continue

    nonempty_count += 1
    origin = np.array([float(v) for v in fg.PlanePositionSequence[0].ImagePositionPatient])
    z = round(float(origin[2]), 4)

    record = {
        "seg_frame_1based": i + 1,
        "z_mm": float(origin[2]),
        "tumor_pixels": pixel_count,
        "ct_z_match": False,
        "ct_sop_uid": "",
        "seg_for_uid": str(getattr(seg, "FrameOfReferenceUID", "")),
        "ct_for_uid": "",
        "frame_of_reference_match": False,
        "orientation_match": False,
        "pixel_spacing_match": False,
        "mapped_pixels": 0,
        "in_bounds_pixels": 0,
        "out_of_bounds_pixels": 0,
        "in_bounds_percent": 0.0,
        "status": ""
    }

    if z not in ct_by_z:
        record["status"] = "NO_EXACT_Z_MATCH"
        rows_out.append(record)
        continue

    exact_z_count += 1
    ct_path, ct_hdr = ct_by_z[z]
    ct = pydicom.dcmread(str(ct_path))
    ct_pixels = ct.pixel_array.astype(np.float32)
    ct_pixels = ct_pixels * float(getattr(ct, "RescaleSlope", 1)) + float(getattr(ct, "RescaleIntercept", 0))

    ct_iop = np.array([float(v) for v in ct.ImageOrientationPatient])
    ct_col_dir, ct_row_dir = ct_iop[:3], ct_iop[3:]
    ct_spacing = np.array([float(v) for v in ct.PixelSpacing])
    ct_origin = np.array([float(v) for v in ct.ImagePositionPatient])

    rr, cc = np.where(mask)
    xyz = (
        origin
        + rr[:, None] * spacing[0] * row_dir
        + cc[:, None] * spacing[1] * col_dir
    )
    delta = xyz - ct_origin
    mapped_rows = np.rint(np.sum(delta * ct_row_dir, axis=1) / ct_spacing[0]).astype(int)
    mapped_cols = np.rint(np.sum(delta * ct_col_dir, axis=1) / ct_spacing[1]).astype(int)
    valid = (
        (mapped_rows >= 0) & (mapped_rows < ct_pixels.shape[0]) &
        (mapped_cols >= 0) & (mapped_cols < ct_pixels.shape[1])
    )

    mapped = np.zeros(ct_pixels.shape, dtype=bool)
    mapped[mapped_rows[valid], mapped_cols[valid]] = True

    ct_for = str(getattr(ct, "FrameOfReferenceUID", ""))
    ct_iop_list = np.array([float(v) for v in ct.ImageOrientationPatient])
    ct_spacing_list = np.array([float(v) for v in ct.PixelSpacing])

    record.update({
        "ct_z_match": True,
        "ct_sop_uid": str(getattr(ct, "SOPInstanceUID", "")),
        "ct_for_uid": ct_for,
        "frame_of_reference_match": record["seg_for_uid"] == ct_for,
        "orientation_match": bool(np.allclose(iop, ct_iop_list, atol=1e-5)),
        "pixel_spacing_match": bool(np.allclose(spacing, ct_spacing_list, atol=1e-5)),
        "mapped_pixels": int(len(rr)),
        "in_bounds_pixels": int(valid.sum()),
        "out_of_bounds_pixels": int((~valid).sum()),
        "in_bounds_percent": float(100.0 * valid.sum() / max(len(rr), 1)),
        "status": "REVIEW_REQUIRED_FOR_UID_MISMATCH" if record["seg_for_uid"] != ct_for else "GEOMETRY_CHECKED"
    })

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(ct_pixels, cmap="gray", vmin=-150, vmax=250)
    if np.any(mapped):
        ax.contour(mapped.astype(np.uint8), levels=[0.5], colors=["magenta"], linewidths=1.0)
    ax.set_title(f"HCC_048 | Mass SEG frame {i+1} | Z={z:.2f} mm | review only")
    ax.axis("off")
    out_path = OUT / f"HCC_048_recon3_mass_frame_{i+1:03d}_z_{z:.2f}.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    rows_out.append(record)
    print(
        f"Frame {i+1} | Z={z:.2f} | pixels={pixel_count} | "
        f"in_bounds={valid.sum()}/{len(rr)} ({record['in_bounds_percent']:.1f}%) | "
        f"FOR_match={record['frame_of_reference_match']}"
    )

csv_path = OUT / "hcc048_recon3_mapping_qc.csv"
if csv_path.exists():
    raise RuntimeError(f"Refusing to overwrite: {csv_path}")

if rows_out:
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        writer.writeheader()
        writer.writerows(rows_out)

print("\nSEG FrameOfReferenceUID:", getattr(seg, "FrameOfReferenceUID", "NOT PRESENT"))
print("CT FrameOfReferenceUID:", getattr(ct_items[0][1], "FrameOfReferenceUID", "NOT PRESENT"))
print("Candidate CT slices:", len(ct_by_z))
print("Non-empty Mass frames:", nonempty_count)
print("Non-empty Mass frames with exact Z match:", exact_z_count)
print("QC CSV:", csv_path)
print("Overlay folder:", OUT)
print("IMPORTANT: Diagnostic overlays only; no mask shift/resampling. Frame of Reference mismatch requires review.")
