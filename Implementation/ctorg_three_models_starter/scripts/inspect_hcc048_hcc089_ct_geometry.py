from pathlib import Path
import csv
import pydicom
import numpy as np

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
OUT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit\hcc048_hcc089_ct_geometry.csv")
TARGETS = {"HCC_048", "HCC_089"}

rows = []
for patient in sorted(TARGETS):
    patient_dir = ROOT / patient
    if not patient_dir.exists():
        print(f"MISSING PATIENT DIRECTORY: {patient_dir}")
        continue

    grouped = {}
    for path in patient_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
            if str(getattr(ds, "Modality", "")) != "CT":
                continue
            uid = str(getattr(ds, "SeriesInstanceUID", ""))
            if not uid:
                continue
            ipp = getattr(ds, "ImagePositionPatient", None)
            iop = getattr(ds, "ImageOrientationPatient", None)
            spacing = getattr(ds, "PixelSpacing", None)
            item = {
                "path": str(path),
                "z": float(ipp[2]) if ipp is not None and len(ipp) >= 3 else None,
                "ipp": [float(x) for x in ipp] if ipp is not None else None,
                "iop": [float(x) for x in iop] if iop is not None else None,
                "spacing": [float(x) for x in spacing] if spacing is not None else None,
                "for_uid": str(getattr(ds, "FrameOfReferenceUID", "")),
                "study_uid": str(getattr(ds, "StudyInstanceUID", "")),
                "series_desc": str(getattr(ds, "SeriesDescription", "")),
                "series_number": str(getattr(ds, "SeriesNumber", "")),
            }
            grouped.setdefault(uid, []).append(item)
        except Exception:
            pass

    for uid, items in grouped.items():
        zs = sorted(x["z"] for x in items if x["z"] is not None)
        first = items[0]
        rows.append({
            "PatientID": patient,
            "SeriesInstanceUID": uid,
            "SeriesDescription": first["series_desc"],
            "SeriesNumber": first["series_number"],
            "StudyInstanceUID": first["study_uid"],
            "local_CT_files": len(items),
            "slices_with_position": len(zs),
            "min_z": min(zs) if zs else "",
            "max_z": max(zs) if zs else "",
            "unique_z_positions": len(set(round(z, 3) for z in zs)),
            "first_IPP": first["ipp"],
            "IOP": first["iop"],
            "PixelSpacing": first["spacing"],
            "FrameOfReferenceUID": first["for_uid"],
            "sample_path": first["path"],
        })

OUT.parent.mkdir(parents=True, exist_ok=True)
fields = list(rows[0].keys()) if rows else []
with OUT.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

for row in rows:
    print(
        f'{row["PatientID"]} | Series {row["SeriesNumber"]} | '
        f'{row["SeriesDescription"]} | files={row["local_CT_files"]} | '
        f'z={row["min_z"]}..{row["max_z"]} | '
        f'unique_z={row["unique_z_positions"]} | '
        f'SeriesUID={row["SeriesInstanceUID"]}'
    )
print(f"\nSaved: {OUT}")
