from pathlib import Path
import numpy as np
import pydicom

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
PATIENTS = ("HCC_003", "HCC_012", "HCC_019")

def vec(v):
    return np.asarray(v, dtype=float)

def get_sequence(frame, shared, name):
    if hasattr(frame, name):
        return getattr(frame, name)[0]
    if shared and hasattr(shared, name):
        return getattr(shared, name)[0]
    raise AttributeError(f"{name} absent from frame and shared groups")

def source_uids(fg):
    out = []
    for deriv in getattr(fg, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = getattr(src, "ReferencedSOPInstanceUID", None)
            if uid:
                out.append(str(uid))
    return out

def seg_number(fg):
    try:
        return int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    except Exception:
        return None

def pixel_to_patient(row, col, ipp, iop, spacing):
    return (vec(ipp)
            + col * spacing[1] * vec(iop[:3])
            + row * spacing[0] * vec(iop[3:]))

for patient in PATIENTS:
    print(f"\n{'='*18} {patient} {'='*18}")
    seg_path = None
    ct_paths = []

    for path in (ROOT / patient).rglob("*.dcm"):
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True)
            if ds.Modality == "SEG":
                seg_path = path
            elif ds.Modality == "CT":
                ct_paths.append(path)
        except Exception:
            pass

    if seg_path is None:
        print("ERROR: SEG not found")
        continue

    seg = pydicom.dcmread(seg_path)
    arr = seg.pixel_array
    frames = seg.PerFrameFunctionalGroupsSequence
    shared = seg.SharedFunctionalGroupsSequence[0] if hasattr(seg, "SharedFunctionalGroupsSequence") else None

    ct_by_uid = {}
    for path in ct_paths:
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True)
            ct_by_uid[str(ds.SOPInstanceUID)] = (path, ds)
        except Exception:
            pass

    candidates = []
    for i, fg in enumerate(frames):
        if seg_number(fg) != 2:
            continue
        mask = arr[i] > 0
        if mask.any():
            refs = [u for u in source_uids(fg) if u in ct_by_uid]
            if refs:
                candidates.append((i, mask, refs))

    if not candidates:
        print("ERROR: no tumor-positive frames with local CT references")
        continue

    i, mask, refs = candidates[len(candidates)//2]
    fg = frames[i]
    try:
        plane = get_sequence(fg, shared, "PlanePositionSequence")
        measures = get_sequence(fg, shared, "PixelMeasuresSequence")
        orient = get_sequence(fg, shared, "PlaneOrientationSequence")
    except AttributeError as exc:
        print("GEOMETRY ERROR:", exc)
        print("Per-frame group tags:", list(fg.keys()))
        print("Shared group tags:", list(shared.keys()) if shared else "none")
        continue

    ipp = vec(plane.ImagePositionPatient)
    spacing = vec(measures.PixelSpacing)
    iop = vec(orient.ImageOrientationPatient)
    rows, cols = np.where(mask)

    print("SEG frame:", i + 1, "| segment:", seg_number(fg))
    print("Mask shape:", mask.shape, "| positive pixels:", int(mask.sum()))
    print("SEG FrameOfReferenceUID:", getattr(seg, "FrameOfReferenceUID", "MISSING"))
    print("SEG ImagePositionPatient:", ipp.tolist())
    print("SEG ImageOrientationPatient:", iop.tolist())
    print("SEG PixelSpacing:", spacing.tolist())
    print("Mask row/column bounds:",
          (int(rows.min()), int(rows.max()), int(cols.min()), int(cols.max())))
    center = pixel_to_patient(rows.mean(), cols.mean(), ipp, iop, spacing)
    print("Mask center patient XYZ:", np.round(center, 3).tolist())
    print("Referenced local CT images:", len(refs))

    for uid in refs:
        path, header = ct_by_uid[uid]
        print("\n CT file:", path.name)
        print(" SOP UID:", uid)
        print(" FrameOfReferenceUID:", getattr(header, "FrameOfReferenceUID", "MISSING"))
        print(" ImagePositionPatient:", vec(header.ImagePositionPatient).tolist())
        print(" ImageOrientationPatient:", vec(header.ImageOrientationPatient).tolist())
        print(" PixelSpacing:", vec(header.PixelSpacing).tolist())
        print(" Rows/Columns:", header.Rows, header.Columns)

print("\nDiagnostic complete. No files were modified.")
