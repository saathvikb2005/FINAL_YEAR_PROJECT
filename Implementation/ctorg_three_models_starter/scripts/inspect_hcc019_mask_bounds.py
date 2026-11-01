import pydicom
import numpy as np
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_019")
ct_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.991595515813772991981994577552"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
               "Modality", "") == "SEG"
)
seg = pydicom.dcmread(str(seg_path), force=True)
pixels = seg.pixel_array

ct_files = []
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT" and str(d.SeriesInstanceUID) == ct_uid:
            ct_files.append(d)
    except Exception:
        pass

ct_files.sort(key=lambda d: float(d.ImagePositionPatient[2]))
ct = ct_files[len(ct_files)//2]

print("=== Image geometry ===")
print("SEG dimensions:", seg.Rows, "x", seg.Columns)
print("CT dimensions:", ct.Rows, "x", ct.Columns)
print("SEG origin:", np.asarray(
    seg.PerFrameFunctionalGroupsSequence[0]
       .PlanePositionSequence[0].ImagePositionPatient, float
).tolist())
print("CT origin:", np.asarray(ct.ImagePositionPatient, float).tolist())
print("SEG spacing:", np.asarray(
    seg.SharedFunctionalGroupsSequence[0]
       .PixelMeasuresSequence[0].PixelSpacing, float
).tolist())
print("CT spacing:", np.asarray(ct.PixelSpacing, float).tolist())

print("\n=== Mask bounds by segment ===")
segments = {}
for item in seg.SegmentSequence:
    segments[int(item.SegmentNumber)] = str(item.SegmentLabel)

for number, label in segments.items():
    all_r, all_c, all_z = [], [], []
    for idx, fg in enumerate(seg.PerFrameFunctionalGroupsSequence):
        current = int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
        if current != number:
            continue
        mask = pixels[idx] > 0
        rr, cc = np.where(mask)
        if len(rr) == 0:
            continue
        all_r.extend([int(rr.min()), int(rr.max())])
        all_c.extend([int(cc.min()), int(cc.max())])
        all_z.append(float(fg.PlanePositionSequence[0].ImagePositionPatient[2]))

    if all_r:
        print(
            f"{number} {label}: "
            f"rows {min(all_r)}-{max(all_r)}, "
            f"columns {min(all_c)}-{max(all_c)}, "
            f"Z {min(all_z):.2f} to {max(all_z):.2f}"
        )

print("\n=== CT series extent ===")
positions = np.asarray([np.asarray(d.ImagePositionPatient, float) for d in ct_files])
print("CT X origin range:", round(float(positions[:, 0].min()), 3),
      "to", round(float(positions[:, 0].max()), 3))
print("CT Y origin range:", round(float(positions[:, 1].min()), 3),
      "to", round(float(positions[:, 1].max()), 3))
print("CT Z range:", round(float(positions[:, 2].min()), 3),
      "to", round(float(positions[:, 2].max()), 3))
