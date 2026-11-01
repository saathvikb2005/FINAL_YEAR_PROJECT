from pathlib import Path
import csv
import numpy as np
import pydicom
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_003")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc003_coordinate_validation_run1")
TARGET_ZS = [-260.0, -207.5, -157.5]
TOL = 0.1

if OUT.exists():
    raise SystemExit(f"STOP: output folder already exists; refusing to overwrite: {OUT}")
OUT.mkdir(parents=True)

def read_header(path):
    return pydicom.dcmread(str(path), stop_before_pixels=True, force=True)

# Index local CT images by SOP Instance UID.
ct_by_sop = {}
seg_path = None
for path in ROOT.rglob("*.dcm"):
    try:
        ds = read_header(path)
        modality = str(getattr(ds, "Modality", ""))
        if modality == "CT":
            sop = str(getattr(ds, "SOPInstanceUID", ""))
            if sop:
                ct_by_sop[sop] = path
        elif modality == "SEG":
            if seg_path is not None:
                raise SystemExit("STOP: multiple SEG objects found; expected one.")
            seg_path = path
    except SystemExit:
        raise
    except Exception:
        continue

if seg_path is None:
    raise SystemExit("STOP: no SEG object found.")

seg = pydicom.dcmread(str(seg_path))
seg_pixels = seg.pixel_array
seg_for = str(getattr(seg, "FrameOfReferenceUID", ""))

segment_labels = {
    int(s.SegmentNumber): str(s.SegmentLabel)
    for s in seg.SegmentSequence
}

def frame_info(index):
    fg = seg.PerFrameFunctionalGroupsSequence[index]
    pos = np.asarray(fg.PlanePositionSequence[0].ImagePositionPatient, dtype=float)
    ori_seq = getattr(fg, "PlaneOrientationSequence", None)
    if ori_seq:
        ori = np.asarray(ori_seq[0].ImageOrientationPatient, dtype=float)
    else:
        ori = np.asarray(
            seg.SharedFunctionalGroupsSequence[0].PlaneOrientationSequence[0].ImageOrientationPatient,
            dtype=float
        )
    pm_seq = getattr(fg, "PixelMeasuresSequence", None)
    if pm_seq:
        spacing = np.asarray(pm_seq[0].PixelSpacing, dtype=float)
    else:
        spacing = np.asarray(
            seg.SharedFunctionalGroupsSequence[0].PixelMeasuresSequence[0].PixelSpacing,
            dtype=float
        )
    segment_no = int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)

    refs = []
    for deriv in getattr(fg, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
            if uid and uid not in refs:
                refs.append(uid)
    return pos, ori, spacing, segment_no, refs

def map_mask_to_ct(mask, pos, ori, spacing, ct):
    rr, cc = np.where(mask)
    out = np.zeros((int(ct.Rows), int(ct.Columns)), dtype=bool)
    if len(rr) == 0:
        return out, 0, 0

    ct_pos = np.asarray(ct.ImagePositionPatient, dtype=float)
    ct_ori = np.asarray(ct.ImageOrientationPatient, dtype=float)
    ct_spacing = np.asarray(ct.PixelSpacing, dtype=float)

    xyz = (
        pos[None, :]
        + cc[:, None] * ori[:3][None, :] * spacing[1]
        + rr[:, None] * ori[3:][None, :] * spacing[0]
    )
    delta = xyz - ct_pos[None, :]
    cols_float = delta @ ct_ori[:3] / ct_spacing[1]
    rows_float = delta @ ct_ori[3:] / ct_spacing[0]

    rows = np.rint(rows_float).astype(int)
    cols = np.rint(cols_float).astype(int)
    inside = (
        (rows >= 0) & (rows < int(ct.Rows)) &
        (cols >= 0) & (cols < int(ct.Columns))
    )
    out[rows[inside], cols[inside]] = True
    return out, int(len(rr)), int(inside.sum())

def select_frame(segment_no, target_z):
    found = []
    for i in range(len(seg.PerFrameFunctionalGroupsSequence)):
        pos, ori, spacing, seg_no, refs = frame_info(i)
        if seg_no == segment_no and abs(float(pos[2]) - target_z) < 0.01:
            found.append((i, pos, ori, spacing, refs))
    if len(found) != 1:
        raise RuntimeError(
            f"Expected one frame for segment {segment_no} at Z={target_z}; found {len(found)}"
        )
    return found[0]

rows_out = []
print("SEG:", seg_path)
print("Local CT SOP instances:", len(ct_by_sop))
print("SEG FrameOfReferenceUID:", seg_for)
print("Output folder:", OUT)

for target_z in TARGET_ZS:
    liver_i, liver_pos, liver_ori, liver_spacing, liver_refs = select_frame(1, target_z)
    tumor_i, tumor_pos, tumor_ori, tumor_spacing, tumor_refs = select_frame(2, target_z)

    if not liver_refs or not tumor_refs:
        raise RuntimeError(f"Missing explicit source references at Z={target_z}")

    # Resolve source CT images explicitly referenced by both frames.
    liver_ct_paths = [ct_by_sop[u] for u in liver_refs if u in ct_by_sop]
    tumor_ct_paths = [ct_by_sop[u] for u in tumor_refs if u in ct_by_sop]
    if not liver_ct_paths or not tumor_ct_paths:
        raise RuntimeError(f"Unresolved local source CT reference at Z={target_z}")

    liver_cts = [pydicom.dcmread(str(p)) for p in liver_ct_paths]
    tumor_cts = [pydicom.dcmread(str(p)) for p in tumor_ct_paths]
    ct = tumor_cts[0]

    # Require all resolved references for these frames to have matching grids.
    all_cts = liver_cts + tumor_cts
    for other in all_cts:
        if str(other.SeriesInstanceUID) != str(ct.SeriesInstanceUID):
            raise RuntimeError(f"Referenced CT series differs at Z={target_z}")
        if list(other.ImagePositionPatient) != list(ct.ImagePositionPatient):
            raise RuntimeError(f"Referenced CT positions differ at Z={target_z}")
        if list(other.ImageOrientationPatient) != list(ct.ImageOrientationPatient):
            raise RuntimeError(f"Referenced CT orientations differ at Z={target_z}")
        if list(other.PixelSpacing) != list(ct.PixelSpacing):
            raise RuntimeError(f"Referenced CT pixel spacing differs at Z={target_z}")

    liver_mask, liver_n, liver_inside = map_mask_to_ct(
        seg_pixels[liver_i] > 0, liver_pos, liver_ori, liver_spacing, ct
    )
    tumor_mask, tumor_n, tumor_inside = map_mask_to_ct(
        seg_pixels[tumor_i] > 0, tumor_pos, tumor_ori, tumor_spacing, ct
    )

    intersection = int(np.logical_and(liver_mask, tumor_mask).sum())
    tumor_on_ct = int(tumor_mask.sum())
    liver_on_ct = int(liver_mask.sum())
    tumor_in_liver_pct = 100.0 * intersection / tumor_on_ct if tumor_on_ct else 0.0
    liver_covered_pct = 100.0 * intersection / liver_on_ct if liver_on_ct else 0.0

    ct_for = str(getattr(ct, "FrameOfReferenceUID", ""))
    for_match = seg_for == ct_for

    rows_out.append({
        "z_mm": target_z,
        "liver_seg_frame": liver_i + 1,
        "tumor_seg_frame": tumor_i + 1,
        "liver_original_pixels": liver_n,
        "tumor_original_pixels": tumor_n,
        "liver_mapped_pixels": liver_on_ct,
        "tumor_mapped_pixels": tumor_on_ct,
        "liver_pixels_inside_ct": liver_inside,
        "tumor_pixels_inside_ct": tumor_inside,
        "common_grid_intersection_pixels": intersection,
        "tumor_pixels_inside_liver_pct": round(tumor_in_liver_pct, 3),
        "liver_pixels_covered_by_tumor_pct": round(liver_covered_pct, 3),
        "seg_ct_frame_of_reference_uid_match": for_match,
        "ct_series_uid": str(ct.SeriesInstanceUID),
        "ct_sop_uid": str(ct.SOPInstanceUID),
        "liver_source_refs_resolved": len(liver_cts),
        "tumor_source_refs_resolved": len(tumor_cts),
    })

    # Render CT with both transformed masks on the same CT grid.
    image = ct.pixel_array.astype(np.float32)
    slope = float(getattr(ct, "RescaleSlope", 1.0))
    intercept = float(getattr(ct, "RescaleIntercept", 0.0))
    image = image * slope + intercept

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(image, cmap="gray", vmin=-150, vmax=250)
    if liver_mask.any():
        ax.contour(liver_mask.astype(np.uint8), levels=[0.5], colors=["lime"], linewidths=1.0)
    if tumor_mask.any():
        ax.contour(tumor_mask.astype(np.uint8), levels=[0.5], colors=["red"], linewidths=1.2)
    ax.set_title(f"HCC_003 | Z={target_z:.1f} mm | Liver=green, Tumor=red")
    ax.axis("off")
    fig.tight_layout()
    image_path = OUT / f"common_grid_overlay_z_{target_z:.1f}.png"
    fig.savefig(image_path, dpi=140)
    plt.close(fig)

    print(f"\nZ={target_z:.1f} mm")
    print("  CT series:", ct.SeriesInstanceUID)
    print("  Liver pixels mapped:", liver_on_ct, "| Tumor pixels mapped:", tumor_on_ct)
    print("  Common-grid intersection:", intersection)
    print("  Tumor pixels inside liver (%):", round(tumor_in_liver_pct, 3))
    print("  UID match:", for_match)
    print("  Overlay:", image_path)

csv_path = OUT / "common_grid_validation_summary.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
    writer.writeheader()
    writer.writerows(rows_out)

print("\nSummary CSV:", csv_path)
print("NOTE: This is a diagnostic; it does not approve cohort eligibility.")
