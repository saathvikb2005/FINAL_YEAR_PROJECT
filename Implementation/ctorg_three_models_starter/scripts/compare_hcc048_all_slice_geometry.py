import pydicom
import numpy as np
from pathlib import Path
from collections import defaultdict

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_048")

candidates = {
    "Recon3_Liver_Phase": "1.3.6.1.4.1.14519.5.2.1.1706.8374.212512542241432476118639218381",
    "Recon2_Pre_Liver": "1.3.6.1.4.1.14519.5.2.1.1706.8374.288936153358575768332977262270",
    "Recon2_Liver_Phase": "1.3.6.1.4.1.14519.5.2.1.1706.8374.671566828617718479968762099982",
}

seg_path = next(
    p for p in base.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True)

ct_by_series = defaultdict(list)
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT":
            uid = str(d.SeriesInstanceUID)
            if uid in candidates.values():
                ct_by_series[uid].append(d)
    except Exception:
        continue

frames = []
for i, fg in enumerate(seg.PerFrameFunctionalGroupsSequence, start=1):
    pos = np.asarray(fg.PlanePositionSequence[0].ImagePositionPatient, float)
    frames.append((i, pos))

print("SEG frames:", len(frames))
print("SEG Frame of Reference:", getattr(seg, "FrameOfReferenceUID", "N/A"))

for name, uid in candidates.items():
    cts = ct_by_series[uid]
    print(f"\n===== {name} =====")
    print("CT slices found:", len(cts))

    if not cts:
        print("Candidate series not found locally.")
        continue

    cts.sort(key=lambda d: float(d.ImagePositionPatient[2]))
    z_values = np.array([float(d.ImagePositionPatient[2]) for d in cts])
    sample = cts[len(cts) // 2]

    offsets = []
    for frame_no, pos in frames:
        nearest_idx = int(np.argmin(np.abs(z_values - pos[2])))
        offsets.append(abs(float(z_values[nearest_idx] - pos[2])))

    offsets = np.asarray(offsets)
    print("CT Frame of Reference:", getattr(sample, "FrameOfReferenceUID", "N/A"))
    print("SEG/CT Frame of Reference match:",
          getattr(seg, "FrameOfReferenceUID", None) ==
          getattr(sample, "FrameOfReferenceUID", None))
    print("CT Z range:", round(z_values.min(), 3), "to", round(z_values.max(), 3))
    print("SEG frames with exact Z match (<=0.01 mm):", int((offsets <= 0.01).sum()))
    print("SEG frames within 0.8 mm:", int((offsets <= 0.8).sum()))
    print("Maximum nearest-slice Z offset (mm):", round(float(offsets.max()), 4))

    print("CT origin:", np.round(np.asarray(sample.ImagePositionPatient, float), 4).tolist())
    print("CT orientation:", np.round(np.asarray(sample.ImageOrientationPatient, float), 4).tolist())
    print("CT spacing:", np.round(np.asarray(sample.PixelSpacing, float), 6).tolist())

shared = seg.SharedFunctionalGroupsSequence[0]
seg_ori = np.asarray(shared.PlaneOrientationSequence[0].ImageOrientationPatient, float)
seg_spacing = np.asarray(shared.PixelMeasuresSequence[0].PixelSpacing, float)
print("\n===== SEG GEOMETRY =====")
print("SEG orientation:", seg_ori.tolist())
print("SEG spacing:", seg_spacing.tolist())
print("SEG rows/columns:", seg.Rows, seg.Columns)
print("SEG sample origin:", np.round(frames[0][1], 4).tolist())
