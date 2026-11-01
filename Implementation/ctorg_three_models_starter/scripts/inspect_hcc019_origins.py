import pydicom
import numpy as np
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_019")
ct_series_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.991595515813772991981994577552"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
               "Modality", "") == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True, force=True)

ct_by_sop = {}
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT" and str(d.SeriesInstanceUID) == ct_series_uid:
            ct_by_sop[str(d.SOPInstanceUID)] = d
    except Exception:
        pass

shared = seg.SharedFunctionalGroupsSequence[0]
seg_iop = np.asarray(shared.PlaneOrientationSequence[0].ImageOrientationPatient, float)
seg_spacing = np.asarray(shared.PixelMeasuresSequence[0].PixelSpacing, float)

print("SEG rows/columns:", seg.Rows, seg.Columns)
print("SEG IOP:", seg_iop.tolist())
print("SEG pixel spacing:", seg_spacing.tolist())
print("SEG Frame of Reference:", seg.FrameOfReferenceUID)
print("")

seen = set()
printed = 0

for idx, fg in enumerate(seg.PerFrameFunctionalGroupsSequence, start=1):
    seg_pos = np.asarray(fg.PlanePositionSequence[0].ImagePositionPatient, float)
    seg_no = int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)

    sources = []
    for deriv in getattr(fg, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
            if uid:
                sources.append(uid)

    for uid in sources:
        ct = ct_by_sop.get(uid)
        if ct is None:
            continue

        key = (seg_no, uid)
        if key in seen:
            continue
        seen.add(key)

        ct_pos = np.asarray(ct.ImagePositionPatient, float)
        ct_iop = np.asarray(ct.ImageOrientationPatient, float)
        ct_spacing = np.asarray(ct.PixelSpacing, float)

        # Project the origin difference onto CT's row, column and slice axes.
        ct_col_dir = ct_iop[:3]
        ct_row_dir = ct_iop[3:]
        ct_normal = np.cross(ct_col_dir, ct_row_dir)
        ct_normal /= np.linalg.norm(ct_normal)
        delta = seg_pos - ct_pos

        print(f"SEG frame {idx}, segment {seg_no}")
        print("  Referenced CT SOP:", uid)
        print("  CT series UID:", ct.SeriesInstanceUID)
        print("  Same FoR:", seg.FrameOfReferenceUID == getattr(ct, "FrameOfReferenceUID", None))
        print("  SEG origin:", np.round(seg_pos, 4).tolist())
        print("  CT origin: ", np.round(ct_pos, 4).tolist())
        print("  SEG IOP:", np.round(seg_iop, 6).tolist())
        print("  CT IOP: ", np.round(ct_iop, 6).tolist())
        print("  CT spacing:", np.round(ct_spacing, 6).tolist())
        print("  Origin delta (SEG - CT):", np.round(delta, 4).tolist())
        print("  Delta along CT row (mm):", round(float(np.dot(delta, ct_row_dir)), 4))
        print("  Delta along CT column (mm):", round(float(np.dot(delta, ct_col_dir)), 4))
        print("  Delta along CT normal (mm):", round(float(np.dot(delta, ct_normal)), 4))
        print("")
        printed += 1
        if printed >= 8:
            break
    if printed >= 8:
        break

print("Distinct segment/source examples printed:", printed)
