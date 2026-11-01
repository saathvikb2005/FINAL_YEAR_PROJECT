import pydicom
import numpy as np
from pathlib import Path
from collections import Counter

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_003")
target_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.281650679207816520863173918688"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True)

ct_index = {}
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT":
            ct_index[str(d.SOPInstanceUID)] = d
    except Exception:
        pass

shared = seg.SharedFunctionalGroupsSequence[0]
seg_ori = np.asarray(
    shared.PlaneOrientationSequence[0].ImageOrientationPatient, float
)
seg_spacing = np.asarray(
    shared.PixelMeasuresSequence[0].PixelSpacing, float
)

checks = Counter()
errors = []
max_origin_error = 0.0
max_spacing_error = 0.0
max_orientation_error = 0.0
max_z_error = 0.0

for frame_no, fg in enumerate(seg.PerFrameFunctionalGroupsSequence, start=1):
    seg_pos = np.asarray(fg.PlanePositionSequence[0].ImagePositionPatient, float)
    source_uids = set()

    for deriv in getattr(fg, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
            if uid:
                source_uids.add(uid)

    if not source_uids:
        errors.append((frame_no, "no source references"))
        continue

    for uid in source_uids:
        ct = ct_index.get(uid)
        if ct is None:
            errors.append((frame_no, "missing source SOP"))
            continue

        if str(ct.SeriesInstanceUID) != target_uid:
            errors.append((frame_no, "source belongs to unexpected series"))
            continue

        ct_pos = np.asarray(ct.ImagePositionPatient, float)
        ct_ori = np.asarray(ct.ImageOrientationPatient, float)
        ct_spacing = np.asarray(ct.PixelSpacing, float)

        # Compare image-plane origins after accounting for reversed orientation.
        # With opposite directions, the SEG origin should coincide with the
        # opposite corner of the CT image grid.
        expected_ct_corner = (
            seg_pos
            + (seg.Columns - 1) * seg_spacing[1] * seg_ori[:3]
            + (seg.Rows - 1) * seg_spacing[0] * seg_ori[3:]
        )

        origin_error = float(np.linalg.norm(expected_ct_corner - ct_pos))
        spacing_error = float(np.max(np.abs(seg_spacing - ct_spacing)))
        orientation_error = float(np.max(np.abs(seg_ori + ct_ori)))
        z_error = abs(float(seg_pos[2] - ct_pos[2]))

        max_origin_error = max(max_origin_error, origin_error)
        max_spacing_error = max(max_spacing_error, spacing_error)
        max_orientation_error = max(max_orientation_error, orientation_error)
        max_z_error = max(max_z_error, z_error)

        checks["source comparisons"] += 1
        if origin_error <= 0.2 and spacing_error <= 0.001 and orientation_error <= 0.001 and z_error <= 0.1:
            checks["geometry matches"] += 1
        else:
            errors.append((
                frame_no,
                f"origin={origin_error:.3f}mm, spacing={spacing_error:.5f}mm, "
                f"orientation={orientation_error:.5f}, z={z_error:.3f}mm"
            ))

print("SEG frames:", len(seg.PerFrameFunctionalGroupsSequence))
print("Source geometry comparisons:", checks["source comparisons"])
print("Comparisons passing stated tolerances:", checks["geometry matches"])
print("Maximum opposite-corner origin error (mm):", round(max_origin_error, 5))
print("Maximum pixel-spacing error (mm):", round(max_spacing_error, 6))
print("Maximum opposite-orientation error:", round(max_orientation_error, 6))
print("Maximum Z-position error (mm):", round(max_z_error, 5))
print("Flagged comparisons:", len(errors))

for item in errors[:20]:
    print("REVIEW:", item)
