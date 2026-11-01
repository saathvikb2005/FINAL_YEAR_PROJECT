from pathlib import Path
import numpy as np
import pydicom
import matplotlib.pyplot as plt

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\overlays")
PATIENTS = ("HCC_012", "HCC_019", "HCC_003")

def segment_number(fg):
    try:
        return int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    except Exception:
        return None

def source_uids(fg):
    uids = []
    for deriv in getattr(fg, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = getattr(src, "ReferencedSOPInstanceUID", None)
            if uid:
                uids.append(str(uid))
    return uids

def ct_pixels(ds):
    arr = ds.pixel_array.astype(np.float32)
    slope = float(getattr(ds, "RescaleSlope", 1))
    intercept = float(getattr(ds, "RescaleIntercept", 0))
    return arr * slope + intercept

OUT.mkdir(parents=True, exist_ok=True)

for patient in PATIENTS:
    print(f"\n========== {patient} ==========")
    seg_path = None
    ct_paths = []

    for p in (ROOT / patient).rglob("*.dcm"):
        try:
            ds = pydicom.dcmread(p, stop_before_pixels=True)
            if ds.Modality == "SEG":
                seg_path = p
            elif ds.Modality == "CT":
                ct_paths.append(p)
        except Exception:
            pass

    if seg_path is None:
        print("SEG not found")
        continue

    seg = pydicom.dcmread(seg_path)
    seg_array = seg.pixel_array
    groups = seg.PerFrameFunctionalGroupsSequence

    ct_by_uid = {}
    for p in ct_paths:
        try:
            ds = pydicom.dcmread(p, stop_before_pixels=True)
            ct_by_uid[str(ds.SOPInstanceUID)] = p
        except Exception:
            pass

    candidates = []
    for i, fg in enumerate(groups):
        if segment_number(fg) != 2:
            continue
        mask = seg_array[i] > 0
        if mask.any():
            refs = source_uids(fg)
            resolved = [uid for uid in refs if uid in ct_by_uid]
            if resolved:
                candidates.append((i, mask, resolved[0]))

    if not candidates:
        print("No tumor-positive frames with a resolved CT reference")
        continue

    i, mask, uid = candidates[len(candidates) // 2]
    ct = pydicom.dcmread(ct_by_uid[uid])
    image = ct_pixels(ct)

    if image.shape != mask.shape:
        print("Dimension mismatch:", image.shape, mask.shape)
        continue

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(image, cmap="gray", vmin=-150, vmax=250)
    ax.contour(mask.astype(np.uint8), levels=[0.5], colors="red", linewidths=0.8)
    ax.set_title(f"{patient} | SEG frame {i+1} | CT reference matched by SOP UID")
    ax.axis("off")

    out_path = OUT / f"{patient}_tumor_overlay.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("Selected SEG frame:", i + 1)
    print("Referenced CT:", uid)
    print("Tumor-positive pixels:", int(mask.sum()))
    print("Overlay saved:", out_path)

print("\nOverlay generation finished.")
