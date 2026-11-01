from pathlib import Path
import pydicom

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
SEG_PATH = ROOT / (
    r"HCC_089\1.3.6.1.4.1.14519.5.2.1.1706.8374.324511982524894820763579219177"
    r"\1.2.276.0.7230010.3.1.3.8323329.2303.1600929169.408163"
    r"\c25aaa91-f29d-4b21-899d-83da89c31303.dcm"
)

seg = pydicom.dcmread(str(SEG_PATH))
per_frame = seg.PerFrameFunctionalGroupsSequence
shared = seg.SharedFunctionalGroupsSequence[0]
seg_iop = [float(v) for v in shared.PlaneOrientationSequence[0].ImageOrientationPatient]
seg_spacing = [float(v) for v in shared.PixelMeasuresSequence[0].PixelSpacing]

def get_position(fg):
    seq = getattr(fg, "PlanePositionSequence", [])
    return [float(v) for v in seq[0].ImagePositionPatient] if seq else None

refs = {}
for i, fg in enumerate(per_frame):
    derivation = getattr(fg, "DerivationImageSequence", [])
    for deriv in derivation:
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
            if uid:
                refs[i] = uid

wanted = set(refs.values())
found = {}
for path in ROOT.joinpath("HCC_089").rglob("*"):
    if not path.is_file():
        continue
    try:
        ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
        uid = str(getattr(ds, "SOPInstanceUID", ""))
        if uid in wanted:
            found[uid] = (path, ds)
    except Exception:
        continue

print("SEG shared orientation:", seg_iop)
print("SEG pixel spacing:", seg_spacing)
print("Referenced CT images found:", len(found), "of", len(wanted))

for frame_index, uid in sorted(refs.items()):
    fg = per_frame[frame_index]
    seg_pos = get_position(fg)
    print(f"\nSEG frame {frame_index + 1}")
    print("  SEG position:", seg_pos)
    print("  Referenced SOP UID:", uid)
    if uid not in found:
        print("  CT image: NOT FOUND")
        continue
    path, ct = found[uid]
    print("  CT path:", path)
    print("  CT series UID:", getattr(ct, "SeriesInstanceUID", ""))
    print("  CT position:", list(map(float, ct.ImagePositionPatient)))
    print("  CT orientation:", list(map(float, ct.ImageOrientationPatient)))
    print("  CT spacing:", list(map(float, ct.PixelSpacing)))
    print("  CT rows/columns:", ct.Rows, ct.Columns)
    print("  CT FrameOfReferenceUID:", getattr(ct, "FrameOfReferenceUID", ""))
    print("  SEG FrameOfReferenceUID:", getattr(seg, "FrameOfReferenceUID", ""))
