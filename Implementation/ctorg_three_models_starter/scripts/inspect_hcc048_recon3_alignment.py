import pydicom
import numpy as np
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_048")
target_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.212512542241432476118639218381"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(
        pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
        "Modality", ""
    ) == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True)

ct_files = []
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT" and str(
            getattr(d, "SeriesInstanceUID", "")
        ) == target_uid:
            ct_files.append(d)
    except Exception:
        pass

ct_files.sort(key=lambda d: float(d.ImagePositionPatient[2]))
ct = ct_files[len(ct_files)//2]

shared = seg.SharedFunctionalGroupsSequence[0]
ori = np.asarray(shared.PlaneOrientationSequence[0].ImageOrientationPatient, float)
spacing = np.asarray(shared.PixelMeasuresSequence[0].PixelSpacing, float)

print("SEG Study UID:", seg.StudyInstanceUID)
print("CT Study UID:", ct.StudyInstanceUID)
print("Same Study UID:", seg.StudyInstanceUID == ct.StudyInstanceUID)
print("SEG FoR UID:", seg.FrameOfReferenceUID)
print("CT FoR UID:", ct.FrameOfReferenceUID)
print("SEG orientation:", ori.tolist())
print("CT orientation:", np.asarray(ct.ImageOrientationPatient, float).tolist())
print("SEG spacing:", spacing.tolist())
print("CT spacing:", np.asarray(ct.PixelSpacing, float).tolist())
print("SEG first position:", np.asarray(
    seg.PerFrameFunctionalGroupsSequence[0]
       .PlanePositionSequence[0].ImagePositionPatient, float
).tolist())
print("SEG last position:", np.asarray(
    seg.PerFrameFunctionalGroupsSequence[-1]
       .PlanePositionSequence[0].ImagePositionPatient, float
).tolist())
print("CT first position:", np.asarray(ct_files[0].ImagePositionPatient, float).tolist())
print("CT last position:", np.asarray(ct_files[-1].ImagePositionPatient, float).tolist())
print("CT slice count:", len(ct_files))
