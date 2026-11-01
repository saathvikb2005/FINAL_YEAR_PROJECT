from pathlib import Path
import pydicom
import numpy as np

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
seg_path = root / (
    r"HCC_089\1.3.6.1.4.1.14519.5.2.1.1706.8374.324511982524894820763579219177"
    r"\1.2.276.0.7230010.3.1.3.8323329.2303.1600929169.408163"
    r"\c25aaa91-f29d-4b21-899d-83da89c31303.dcm"
)

ds = pydicom.dcmread(str(seg_path))
pixels = ds.pixel_array
frames = ds.PerFrameFunctionalGroupsSequence

print("Tumor candidate frames (segment 2 = Mass):")
for i, fg in enumerate(frames):
    sid = getattr(fg, "SegmentIdentificationSequence", [])
    if not sid or int(sid[0].ReferencedSegmentNumber) != 2:
        continue

    mask = pixels[i]
    n = int(np.count_nonzero(mask))
    if n == 0:
        continue

    pseq = getattr(fg, "PlanePositionSequence", [])
    pos = [float(v) for v in pseq[0].ImagePositionPatient] if pseq else None
    rr, cc = np.where(mask > 0)
    bbox = (int(rr.min()), int(rr.max()), int(cc.min()), int(cc.max()))

    print(
        f"Frame={i+1}, Z={pos[2] if pos else None:.3f}, "
        f"pixels={n}, bbox_rows_cols={bbox}"
    )

print("\nReferenced CT series UID:")
print("1.3.6.1.4.1.14519.5.2.1.1706.8374.187699732728809609459703")
