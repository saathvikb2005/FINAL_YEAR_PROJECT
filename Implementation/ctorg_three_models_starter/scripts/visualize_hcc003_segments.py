import pydicom
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_003")
out = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc003_segment_diagnostics")
out.mkdir(parents=True, exist_ok=True)

seg_path = next(
    p for p in base.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
ds = pydicom.dcmread(str(seg_path))
pixels = ds.pixel_array

names = {1: "Liver", 2: "Mass / Tumor", 3: "Portal vein", 4: "Aorta"}
targets = [-260.0, -207.5, -157.5]

for target in targets:
    masks = {}
    for i, fg in enumerate(ds.PerFrameFunctionalGroupsSequence):
        seg_no = int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
        z = float(fg.PlanePositionSequence[0].ImagePositionPatient[2])
        if abs(z - target) < 0.01:
            masks[seg_no] = pixels[i] > 0

    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    for ax, seg_no in zip(axes, [1, 2, 3, 4]):
        mask = masks.get(seg_no)
        if mask is None:
            ax.set_title(names[seg_no] + "\nMissing")
            ax.axis("off")
            continue

        ax.imshow(mask, interpolation="nearest")
        ax.set_title(f"{names[seg_no]}\n{int(mask.sum()):,} pixels")
        ax.axis("off")

    fig.suptitle(f"HCC_003 SEG masks at Z = {target} mm")
    fig.tight_layout()
    path = out / f"HCC003_segments_z_{target:.1f}.png"
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(path)

print("\nDiagnostics saved to:", out)
