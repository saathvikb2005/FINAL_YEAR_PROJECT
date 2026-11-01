from pathlib import Path
import csv
import pydicom
import numpy as np

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
REPORT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc_seg_frame_reference_geometry.csv")

def fmt(value):
    if value is None:
        return None
    try:
        return [round(float(x), 5) for x in value]
    except TypeError:
        return str(value)

def find_dicom(patient, modality):
    result = []
    for path in (ROOT / patient).rglob("*.dcm"):
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True)
            if str(getattr(ds, "Modality", "")) == modality:
                result.append((path, ds))
        except Exception:
            pass
    return result

with REPORT.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

for patient in ("HCC_003", "HCC_019", "HCC_012"):
    print(f"\n{'='*20} {patient} {'='*20}")

    segs = find_dicom(patient, "SEG")
    cts = find_dicom(patient, "CT")
    print("SEG objects:", len(segs), "| CT instances:", len(cts))

    for seg_path, seg in segs:
        print("\nSEG:", seg_path.name)
        print("SEG Series UID:", getattr(seg, "SeriesInstanceUID", None))
        print("SEG FrameOfReferenceUID:", getattr(seg, "FrameOfReferenceUID", None))
        print("SEG dimensions:", getattr(seg, "Rows", None), getattr(seg, "Columns", None))
        print("SEG Shared orientation:", fmt(
            getattr(getattr(seg, "SharedFunctionalGroupsSequence", [None])[0],
                    "PlaneOrientationSequence", [None])[0].ImageOrientationPatient
            if hasattr(seg, "SharedFunctionalGroupsSequence") and
               hasattr(seg.SharedFunctionalGroupsSequence[0], "PlaneOrientationSequence")
            else None
        ))
        print("SEG Shared pixel measures:", end=" ")
        try:
            pm = seg.SharedFunctionalGroupsSequence[0].PixelMeasuresSequence[0]
            print("spacing", fmt(pm.PixelSpacing), "thickness", getattr(pm, "SliceThickness", None))
        except Exception:
            print("not available in shared groups")

        patient_rows = [r for r in rows if r.get("PatientID") == patient
                        and r.get("frame_status") == "REFERENCE_FOUND"]
        deltas = sorted(
            patient_rows,
            key=lambda r: float(r.get("in_plane_delta_mm") or 0),
            reverse=True
        )
        print("Largest in-plane discrepancies from report:")
        for r in deltas[:3]:
            print({k: r.get(k) for k in (
                "frame", "segment_number", "reference_uid", "CT_series",
                "frame_of_reference_match", "orientation_match",
                "position_delta_mm", "in_plane_delta_mm", "normal_delta_mm"
            )})

        # Show geometry for the CT instances implicated by the largest discrepancies.
        bad_uids = {r.get("reference_uid") for r in deltas[:3]}
        ct_by_uid = {
            str(getattr(ds, "SOPInstanceUID", "")): ds
            for _, ds in cts
        }
        for uid in bad_uids:
            ds = ct_by_uid.get(uid)
            if ds is None:
                print("Referenced CT UID not found locally:", uid)
                continue
            print("\nReferenced CT:", uid)
            print("  Series:", getattr(ds, "SeriesInstanceUID", None))
            print("  FrameOfReferenceUID:", getattr(ds, "FrameOfReferenceUID", None))
            print("  Position:", fmt(getattr(ds, "ImagePositionPatient", None)))
            print("  Orientation:", fmt(getattr(ds, "ImageOrientationPatient", None)))
            print("  PixelSpacing:", fmt(getattr(ds, "PixelSpacing", None)))
