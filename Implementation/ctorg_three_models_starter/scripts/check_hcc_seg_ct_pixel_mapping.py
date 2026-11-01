from pathlib import Path
import numpy as np
import pydicom

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
PATIENTS = ("HCC_003", "HCC_012", "HCC_019")

def v(x):
    return np.asarray(x, dtype=float)

def seq(frame, shared, name):
    if hasattr(frame, name):
        return getattr(frame, name)[0]
    return getattr(shared, name)[0]

def refs_for(frame):
    refs = []
    for deriv in getattr(frame, "DerivationImageSequence", []):
        for src in getattr(deriv, "SourceImageSequence", []):
            uid = getattr(src, "ReferencedSOPInstanceUID", None)
            if uid:
                refs.append(str(uid))
    return refs

def segment_no(frame):
    try:
        return int(frame.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    except Exception:
        return None

def patient_xyz(row, col, ipp, iop, spacing):
    return (ipp + col * spacing[1] * iop[:3]
            + row * spacing[0] * iop[3:])

def xyz_to_pixel(xyz, ct):
    ipp = v(ct.ImagePositionPatient)
    iop = v(ct.ImageOrientationPatient)
    spacing = v(ct.PixelSpacing)
    delta = xyz - ipp
    col = np.dot(delta, iop[:3]) / spacing[1]
    row = np.dot(delta, iop[3:]) / spacing[0]
    return row, col

for patient in PATIENTS:
    print(f"\n{'='*15} {patient} {'='*15}")
    seg_path = None
    ct_paths = []

    for path in (ROOT / patient).rglob("*.dcm"):
        try:
            h = pydicom.dcmread(path, stop_before_pixels=True)
            if h.Modality == "SEG":
                seg_path = path
            elif h.Modality == "CT":
                ct_paths.append(path)
        except Exception:
            pass

    if seg_path is None:
        print("SEG not found")
        continue

    seg = pydicom.dcmread(seg_path)
    pixels = seg.pixel_array
    frames = seg.PerFrameFunctionalGroupsSequence
    shared = seg.SharedFunctionalGroupsSequence[0]
    ct_by_uid = {}

    for path in ct_paths:
        try:
            h = pydicom.dcmread(path, stop_before_pixels=True)
            ct_by_uid[str(h.SOPInstanceUID)] = (path, h)
        except Exception:
            pass

    candidates = []
    for i, frame in enumerate(frames):
        if segment_no(frame) != 2:
            continue
        mask = pixels[i] > 0
        if mask.any():
            matched = [u for u in refs_for(frame) if u in ct_by_uid]
            if matched:
                candidates.append((i, mask, matched))

    if not candidates:
        print("No matching tumor frame")
        continue

    i, mask, matched = candidates[len(candidates)//2]
    frame = frames[i]
    pos = seq(frame, shared, "PlanePositionSequence")
    ori = seq(frame, shared, "PlaneOrientationSequence")
    pm = seq(frame, shared, "PixelMeasuresSequence")
    ipp = v(pos.ImagePositionPatient)
    iop = v(ori.ImageOrientationPatient)
    spacing = v(pm.PixelSpacing)

    rr, cc = np.where(mask)
    points = [
        (rr.mean(), cc.mean(), "mask center"),
        (rr.min(), cc.min(), "top-left bound"),
        (rr.min(), cc.max(), "top-right bound"),
        (rr.max(), cc.min(), "bottom-left bound"),
        (rr.max(), cc.max(), "bottom-right bound"),
    ]

    print("SEG frame:", i + 1, "| positive pixels:", int(mask.sum()))
    print("SEG FrameOfReferenceUID:", getattr(seg, "FrameOfReferenceUID", "MISSING"))

    for uid in matched:
        path, ct = ct_by_uid[uid]
        print("\nCT:", path.name)
        print("CT FrameOfReferenceUID:", getattr(ct, "FrameOfReferenceUID", "MISSING"))
        same_for = (
            getattr(seg, "FrameOfReferenceUID", None)
            == getattr(ct, "FrameOfReferenceUID", None)
        )
        print("FrameOfReferenceUID matches:", same_for)
        print("CT dimensions:", (int(ct.Rows), int(ct.Columns)))

        for r, c, label in points:
            xyz = patient_xyz(r, c, ipp, iop, spacing)
            cr, cc = xyz_to_pixel(xyz, ct)
            inside = 0 <= cr < ct.Rows and 0 <= cc < ct.Columns
            print(f"{label}: CT row={cr:.2f}, col={cc:.2f}, inside={inside}")

        if not same_for:
            print("WARNING: pixel mapping is provisional because coordinate frames differ.")

print("\nMapping diagnostic complete; source files unchanged.")
