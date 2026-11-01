import pydicom
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_019")
out = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc019_overlay_review")
out.mkdir(parents=True, exist_ok=True)

ct_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.991595515813772991981994577552"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
               "Modality", "") == "SEG"
)
seg = pydicom.dcmread(str(seg_path), force=True)
seg_pixels = seg.pixel_array

ct_by_sop = {}
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), force=True)
        if getattr(d, "Modality", "") == "CT" and str(d.SeriesInstanceUID) == ct_uid:
            ct_by_sop[str(d.SOPInstanceUID)] = d
    except Exception:
        pass

# Choose three tumor-positive SEG frames, spaced across the annotated tumor.
tumor_frames = []
for idx, fg in enumerate(seg.PerFrameFunctionalGroupsSequence):
    segment = int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    if segment == 2 and np.any(seg_pixels[idx] > 0):
        tumor_frames.append(idx)

if not tumor_frames:
    raise RuntimeError("No positive tumor frames found in segment 2.")

selected = [tumor_frames[0], tumor_frames[len(tumor_frames)//2], tumor_frames[-1]]

for idx in selected:
    fg = seg.PerFrameFunctionalGroupsSequence[idx]
    z = float(fg.PlanePositionSequence[0].ImagePositionPatient[2])
    mask = seg_pixels[idx] > 0

    refs = []
    for deriv in getattr(fg, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
            if uid in ct_by_sop:
                refs.append(uid)

    if not refs:
        print(f"Frame {idx+1}, Z={z}: no local source CT reference; skipped.")
        continue

    ct = ct_by_sop[refs[0]]
    image = ct.pixel_array.astype(np.float32)
    image = image * float(getattr(ct, "RescaleSlope", 1)) + float(getattr(ct, "RescaleIntercept", 0))

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(image, cmap="gray", vmin=-100, vmax=300)
    ax.contour(mask.astype(np.uint8), levels=[0.5], linewidths=1.2)
    ax.set_title(f"HCC_019 | SEG frame {idx+1} | Z={z:.2f} mm")
    ax.axis("off")

    filename = out / f"HCC019_frame_{idx+1:03d}_z_{z:.2f}.png"
    fig.savefig(filename, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(filename)

print("Overlay review files saved:", out)
