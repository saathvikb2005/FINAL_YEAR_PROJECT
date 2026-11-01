from pathlib import Path
import pydicom
import numpy as np

p = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_048\1.3.6.1.4.1.14519.5.2.1.1706.8374.191238202133507320458118565112\1.3.6.1.4.1.14519.5.2.1.1706.8374.299766419358710200971072115544\08c174be-7d19-474b-a435-0d4188681342.dcm")

ds = pydicom.dcmread(str(p), force=True)
print("Modality:", ds.Modality)
print("Study UID:", ds.StudyInstanceUID)
print("Frame of Reference UID:", getattr(ds, "FrameOfReferenceUID", "MISSING"))
print("Number of frames:", ds.NumberOfFrames)
print("Rows x columns:", ds.Rows, "x", ds.Columns)

shared = ds.SharedFunctionalGroupsSequence[0]
pm = shared.PixelMeasuresSequence[0]
po = shared.PlaneOrientationSequence[0]
print("Pixel spacing:", list(pm.PixelSpacing))
print("Slice thickness:", getattr(pm, "SliceThickness", "MISSING"))
print("Orientation:", list(po.ImageOrientationPatient))

positions = []
for i, fg in enumerate(ds.PerFrameFunctionalGroupsSequence):
    pp = getattr(fg, "PlanePositionSequence", [])
    if pp:
        positions.append((i + 1, [float(v) for v in pp[0].ImagePositionPatient]))

print("Frames with positions:", len(positions))
print("First 5 positions:", positions[:5])
print("Last 5 positions:", positions[-5:])

print("\nSegment definitions:")
for s in ds.SegmentSequence:
    print(
        "Number:", s.SegmentNumber,
        "| Label:", s.SegmentLabel,
        "| Description:", getattr(s, "SegmentDescription", "")
    )

print("\nReferenced series sequence count:",
      len(getattr(ds, "ReferencedSeriesSequence", [])))
