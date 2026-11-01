import pydicom
import numpy as np

p = r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_048\1.3.6.1.4.1.14519.5.2.1.1706.8374.191238202133507320458118565112\1.3.6.1.4.1.14519.5.2.1.1706.8374.299766419358710200971072115544\08c174be-7d19-474b-a435-0d4188681342.dcm"
ds = pydicom.dcmread(p)
pixels = ds.pixel_array
frames = ds.PerFrameFunctionalGroupsSequence

for segment_number in (1, 2, 3, 4):
    found = []
    for i, fg in enumerate(frames):
        ids = getattr(fg, "SegmentIdentificationSequence", [])
        if not ids or int(ids[0].ReferencedSegmentNumber) != segment_number:
            continue
        if np.any(pixels[i]):
            pos = fg.PlanePositionSequence[0].ImagePositionPatient
            found.append((i + 1, round(float(pos[2]), 2), int(pixels[i].sum())))
    print(f"\nSegment {segment_number}: {len(found)} non-empty frames")
    if segment_number == 2:
        print("Tumor-positive frames (frame, Z, pixels):")
        print(found)
