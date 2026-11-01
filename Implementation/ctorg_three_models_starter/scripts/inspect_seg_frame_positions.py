from pathlib import Path
import pydicom

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")

def val(x):
    return [round(float(v), 4) for v in x] if x is not None else None

def get_nested_reference(frame_group):
    refs = []
    for item in getattr(frame_group, "DerivationImageSequence", []):
        for source in getattr(item, "SourceImageSequence", []):
            refs.append(str(getattr(source, "ReferencedSOPInstanceUID", "")))
    return refs

for patient in ("HCC_003", "HCC_019", "HCC_012"):
    seg_files = []
    for p in (ROOT / patient).rglob("*.dcm"):
        try:
            ds = pydicom.dcmread(p, stop_before_pixels=True)
            if getattr(ds, "Modality", "") == "SEG":
                seg_files.append((p, ds))
        except Exception:
            pass

    print(f"\n{'='*18} {patient} {'='*18}")
    if not seg_files:
        print("No SEG found")
        continue

    path, ds = seg_files[0]
    groups = getattr(ds, "PerFrameFunctionalGroupsSequence", [])
    print("SEG file:", path)
    print("Frame count:", len(groups))
    print("Shared orientation:", end=" ")
    try:
        print(val(ds.SharedFunctionalGroupsSequence[0].PlaneOrientationSequence[0].ImageOrientationPatient))
    except Exception:
        print("not available")

    indices = sorted(set(list(range(min(3, len(groups)))) +
                         list(range(max(0, len(groups)-3), len(groups)))))
    for i in indices:
        fg = groups[i]
        pos = None
        orient = None
        segment = None
        try:
            pos = val(fg.PlanePositionSequence[0].ImagePositionPatient)
        except Exception:
            pass
        try:
            orient = val(fg.PlaneOrientationSequence[0].ImageOrientationPatient)
        except Exception:
            pass
        try:
            segment = fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber
        except Exception:
            pass
        print({
            "frame_index_1based": i + 1,
            "segment_number": segment,
            "position": pos,
            "orientation": orient,
            "source_CT_SOP_UIDs": get_nested_reference(fg)
        })
