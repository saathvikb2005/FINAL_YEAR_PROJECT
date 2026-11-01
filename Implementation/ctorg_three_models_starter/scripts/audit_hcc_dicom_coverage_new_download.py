from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd
import pydicom

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC")
patient_root = root / "hcc_tace_seg"
out = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit")
metadata_path = root / "metadata" / "metadata.csv"

if not patient_root.is_dir():
    raise FileNotFoundError(f"DICOM folder not found: {patient_root}")

meta = pd.read_csv(metadata_path, low_memory=False)
expected = meta.copy()
expected["SeriesInstanceUID"] = expected["SeriesInstanceUID"].astype(str).str.strip()
expected = expected.drop_duplicates("SeriesInstanceUID").set_index("SeriesInstanceUID")

series = defaultdict(lambda: {
    "PatientID": "",
    "Modality": "",
    "SeriesDescription": "",
    "files": 0,
    "sop_uids": [],
    "header_errors": 0,
})

header_errors = []
files_scanned = 0
dicom_candidates = 0

for path in patient_root.rglob("*"):
    if not path.is_file() or path.suffix.lower() != ".dcm":
        continue

    files_scanned += 1
    try:
        ds = pydicom.dcmread(
            str(path),
            stop_before_pixels=True,
            force=True,
            specific_tags=[
                "PatientID", "SeriesInstanceUID", "SeriesDescription",
                "Modality", "SOPInstanceUID"
            ],
        )

        modality = str(getattr(ds, "Modality", "")).strip().upper()
        uid = str(getattr(ds, "SeriesInstanceUID", "")).strip()
        sop = str(getattr(ds, "SOPInstanceUID", "")).strip()

        if modality not in {"CT", "SEG"} or not uid:
            header_errors.append({
                "path": str(path),
                "error": f"Missing/unsupported modality or SeriesInstanceUID: {modality!r}, {uid!r}",
            })
            continue

        dicom_candidates += 1
        item = series[uid]
        item["PatientID"] = str(getattr(ds, "PatientID", "")).strip()
        item["Modality"] = modality
        item["SeriesDescription"] = str(getattr(ds, "SeriesDescription", "")).strip()
        item["files"] += 1
        if sop:
            item["sop_uids"].append(sop)

    except Exception as exc:
        header_errors.append({"path": str(path), "error": repr(exc)})

rows = []
duplicate_sop_rows = []

for uid, item in series.items():
    sop_counts = Counter(item["sop_uids"])
    duplicate_sops = {sop: count for sop, count in sop_counts.items() if count > 1}

    rows.append({
        "SeriesInstanceUID": uid,
        "PatientID": item["PatientID"],
        "Modality": item["Modality"],
        "SeriesDescription": item["SeriesDescription"],
        "local_file_count": item["files"],
        "unique_SOPInstanceUIDs": len(sop_counts),
        "duplicate_SOPInstanceUID_count": len(duplicate_sops),
        "metadata_series_found": uid in expected.index,
        "metadata_patient_match": (
            str(expected.loc[uid, "PatientID"]).strip() == item["PatientID"]
            if uid in expected.index else False
        ),
        "metadata_modality_match": (
            str(expected.loc[uid, "Modality"]).strip().upper() == item["Modality"]
            if uid in expected.index else False
        ),
    })

    for sop, count in duplicate_sops.items():
        duplicate_sop_rows.append({
            "SeriesInstanceUID": uid,
            "SOPInstanceUID": sop,
            "occurrences": count,
        })

inventory = pd.DataFrame(rows)
if inventory.empty:
    inventory = pd.DataFrame(columns=[
        "SeriesInstanceUID", "PatientID", "Modality", "SeriesDescription",
        "local_file_count", "unique_SOPInstanceUIDs",
        "duplicate_SOPInstanceUID_count", "metadata_series_found",
        "metadata_patient_match", "metadata_modality_match"
    ])

local_uids = set(inventory["SeriesInstanceUID"].astype(str))
expected_uids = set(expected.index.astype(str))
missing_uids = expected_uids - local_uids
unexpected_uids = local_uids - expected_uids

missing = expected.loc[sorted(missing_uids)].reset_index()
unexpected = inventory[inventory["SeriesInstanceUID"].isin(unexpected_uids)].copy()

inventory_path = out / "hcc_local_series_inventory_new_download.csv"
missing_path = out / "hcc_metadata_series_missing_new_download.csv"
unexpected_path = out / "hcc_unexpected_local_series_new_download.csv"
errors_path = out / "hcc_dicom_header_errors_new_download.csv"
duplicates_path = out / "hcc_duplicate_sop_uids_new_download.csv"

inventory.to_csv(inventory_path, index=False)
missing.to_csv(missing_path, index=False)
unexpected.to_csv(unexpected_path, index=False)
pd.DataFrame(header_errors).to_csv(errors_path, index=False)
pd.DataFrame(duplicate_sop_rows).to_csv(duplicates_path, index=False)

print("=== NEW DOWNLOAD DICOM COVERAGE ===")
print("DICOM files scanned:", files_scanned)
print("Recognized CT/SEG files:", dicom_candidates)
print("Header/identity errors:", len(header_errors))
print("Expected metadata series:", len(expected_uids))
print("Local series discovered:", len(local_uids))
print("Expected series missing locally:", len(missing_uids))
print("Unexpected local series:", len(unexpected_uids))

print("\n=== LOCAL SERIES COUNTS BY MODALITY ===")
print(inventory["Modality"].value_counts(dropna=False).to_string())

print("\n=== METADATA MATCH VALIDATION ===")
if not inventory.empty:
    print("Patient ID mismatches:", int((~inventory["metadata_patient_match"] & inventory["metadata_series_found"]).sum()))
    print("Modality mismatches:", int((~inventory["metadata_modality_match"] & inventory["metadata_series_found"]).sum()))
    print("Series with repeated SOP UIDs:", int((inventory["duplicate_SOPInstanceUID_count"] > 0).sum()))

print("\n=== MISSING SERIES BY MODALITY ===")
if not missing.empty and "Modality" in missing.columns:
    print(missing["Modality"].value_counts(dropna=False).to_string())
else:
    print("None")

print("\n=== SAMPLE MISSING SERIES ===")
print(missing[[c for c in ["PatientID", "Modality", "SeriesDescription", "SeriesInstanceUID"] if c in missing.columns]].head(15).to_string(index=False))

print("\n=== REPORTS ===")
for p in [inventory_path, missing_path, unexpected_path, errors_path, duplicates_path]:
    print(p)
