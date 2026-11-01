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
        if (getattr(d, "Modality", "") == "CT"
                and str(getattr(d, "SeriesInstanceUID", "")) == ct_series_uid):
            ct_by_sop[str(d.SOPInstanceUID)] = d
    except Exception:
        pass

shared = seg.SharedFunctionalGroupsSequence[0]
seg_iop = np.asarray(shared.PlaneOrientationSequence[0].ImageOrientationPatient, float)
seg_spacing = np.asarray(shared.PixelMeasuresSequence[0].PixelSpacing, float)

# DICOM IOP: first triplet = increasing column; second = increasing row.
col_dir = seg_iop[:3]
row_dir = seg_iop[3:]
normal = np.cross(col_dir, row_dir)
normal /= np.linalg.norm(normal)

records = []
no_ref = 0
unmatched = 0

for idx, fg in enumerate(seg.PerFrameFunctionalGroupsSequence, start=1):
    seg_pos = np.asarray(fg.PlanePositionSequence[0].ImagePositionPatient, float)

    source_uids = []
    for deriv in getattr(fg, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = getattr(src, "ReferencedSOPInstanceUID", None)
            if uid:
                source_uids.append(str(uid))

    source_uids = list(dict.fromkeys(source_uids))
    if not source_uids:
        no_ref += 1
        continue

    matched = [ct_by_sop[u] for u in source_uids if u in ct_by_sop]
    if not matched:
        unmatched += 1
        continue

    # Compare against each locally available referenced CT image.
    for ct in matched:
        ct_pos = np.asarray(ct.ImagePositionPatient, float)
        ct_iop = np.asarray(ct.ImageOrientationPatient, float)
        ct_col = ct_iop[:3]
        ct_row = ct_iop[3:]
        ct_normal = np.cross(ct_col, ct_row)
        ct_normal /= np.linalg.norm(ct_normal)

        delta = seg_pos - ct_pos
        row_mm = float(np.dot(delta, ct_row))
        col_mm = float(np.dot(delta, ct_col))
        slice_mm = float(np.dot(delta, ct_normal))

        records.append({
            "frame": idx,
            "segment": int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber),
            "ct_sop": str(ct.SOPInstanceUID),
            "row_offset_px": row_mm / float(ct.PixelSpacing[0]),
            "col_offset_px": col_mm / float(ct.PixelSpacing[1]),
            "slice_offset_mm": slice_mm,
            "euclidean_delta_mm": float(np.linalg.norm(delta)),
        })

print("SEG frames:", len(seg.PerFrameFunctionalGroupsSequence))
print("Local CT SOP instances in referenced series:", len(ct_by_sop))
print("Frames without source references:", no_ref)
print("Frames whose source references did not resolve:", unmatched)
print("Frame-to-CT comparisons:", len(records))

if records:
    print("\nLargest Euclidean position differences:")
    for r in sorted(records, key=lambda x: x["euclidean_delta_mm"], reverse=True)[:12]:
        print(
            f"frame={r['frame']:3d} segment={r['segment']} "
            f"row_px={r['row_offset_px']:+.3f} "
            f"col_px={r['col_offset_px']:+.3f} "
            f"slice_mm={r['slice_offset_mm']:+.3f} "
            f"distance_mm={r['euclidean_delta_mm']:.3f}"
        )

    print("\nMaximum absolute offsets:")
    print("Row pixels:", round(max(abs(r["row_offset_px"]) for r in records), 4))
    print("Column pixels:", round(max(abs(r["col_offset_px"]) for r in records), 4))
    print("Slice mm:", round(max(abs(r["slice_offset_mm"]) for r in records), 4))
