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
seg = pydicom.dcmread(str(seg_path))

shared = seg.SharedFunctionalGroupsSequence[0]
seg_ori = np.array(
    shared.PlaneOrientationSequence[0].PlaneOrientationSequence[0].ImageOrientationPatient
    if False else shared.PlaneOrientationSequence[0].ImageOrientationPatient,
    dtype=float
)
seg_spacing = np.array(
    shared.PixelMeasuresSequence[0].PixelSpacing, dtype=float
)

# Find first and last tumor-segment frame positions.
tumor_positions = []
for frame in seg.PerFrameFunctionalGroupsSequence:
    if int(frame.SegmentIdentificationSequence[0].ReferencedSegmentNumber) == 2:
        tumor_positions.append(
            np.array(frame.PlanePositionSequence[0].ImagePositionPatient, dtype=float)
        )

# DICOM pixel-to-patient mapping: origin + column*column_direction*column_spacing
# + row*row_direction*row_spacing.
def patient_point(origin, ori, spacing, row, col):
    return (
        origin
        + ori[:3] * col * spacing[1]
        + ori[3:] * row * spacing[0]
    )

# SEG image corners at representative tumor slices.
seg_origin = tumor_positions[len(tumor_positions)//2]
corners = [
    patient_point(seg_origin, seg_ori, seg_spacing, r, c)
    for r, c in [(0, 0), (0, 511), (511, 0), (511, 511)]
]

print("SEG orientation:", seg_ori.tolist())
print("SEG spacing:", seg_spacing.tolist())
print("Representative tumor-frame origin:", seg_origin.tolist())
print("\nCandidate CT series geometry:")

seen = set()
for path in root.rglob("*.dcm"):
    try:
        ds = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True
        )
        if getattr(ds, "Modality", "") != "CT":
            continue
        uid = str(ds.SeriesInstanceUID)
        if uid in seen:
            continue
        seen.add(uid)

        ori = np.array(ds.ImageOrientationPatient, dtype=float)
        spacing = np.array(ds.PixelSpacing, dtype=float)
        origin = np.array(ds.ImagePositionPatient, dtype=float)

        # Project the SEG's representative image corners into this CT plane.
        # The CT origin used here is only a sample; per-slice positions are
        # checked separately in the next step.
        delta = np.array([p - origin for p in corners])
        cols = delta @ ori[:3] / spacing[1]
        rows = delta @ ori[3:] / spacing[0]

        print("\nDescription:", ds.SeriesDescription)
        print("Series UID:", uid)
        print("Frame UID match:", ds.FrameOfReferenceUID == seg.FrameOfReferenceUID)
        print("CT orientation:", ori.tolist())
        print("CT spacing:", spacing.tolist())
        print("Sample origin:", origin.tolist())
        print("Projected SEG corner rows:", np.round(rows, 2).tolist())
        print("Projected SEG corner cols:", np.round(cols, 2).tolist())
    except Exception as e:
        continue
