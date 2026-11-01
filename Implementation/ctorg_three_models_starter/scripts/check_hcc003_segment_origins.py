import pydicom
import numpy as np
from pathlib import Path

root = Path(
    r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC"
    r"\hcc_tace_seg\HCC_003"
)

seg_path = next(
    p for p in root.rglob("*.dcm")
    if pydicom.dcmread(
        str(p), stop_before_pixels=True, force=True
    ).Modality == "SEG"
)

ds = pydicom.dcmread(str(seg_path), stop_before_pixels=True)

targets = [-260.0, -207.5, -157.5]
records = []

for i, frame in enumerate(ds.PerFrameFunctionalGroupsSequence):
    seg_no = int(
        frame.SegmentIdentificationSequence[0].ReferencedSegmentNumber
    )
    pos = np.asarray(
        frame.PlanePositionSequence[0].ImagePositionPatient,
        dtype=float
    )
    z = round(float(pos[2]), 3)

    if any(abs(z - target) < 0.01 for target in targets):
        records.append((seg_no, i + 1, z, pos))

print("SEG:", seg_path)

for target in targets:
    print(f"\nTARGET Z = {target} mm")
    selected = [r for r in records if r[2] == target]

    for seg_no, frame_no, z, pos in selected:
        print(
            f"Segment {seg_no}, frame {frame_no}: "
            f"IPP = {np.round(pos, 4).tolist()}"
        )

    if len(selected) > 1:
        origins = np.array([r[3] for r in selected])
        print(
            "Maximum origin difference (mm):",
            np.round(np.ptp(origins, axis=0), 4).tolist()
        )
