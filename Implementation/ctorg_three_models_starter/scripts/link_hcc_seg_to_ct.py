from pathlib import Path
import pandas as pd

out = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"
root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg")

ct = pd.read_csv(out / "hcc_ct_series_candidates.csv", low_memory=False)
seg = pd.read_csv(out / "hcc_seg_pixel_and_reference_audit.csv", low_memory=False)

# Index CT records by their exact Series Instance UID.
ct_index = {}
for _, row in ct.iterrows():
    uid = str(row.get("SeriesInstanceUID", "")).strip()
    if uid and uid.lower() != "nan":
        ct_index.setdefault(uid, []).append(row)

results = []

for _, row in seg.iterrows():
    patient = str(row.get("PatientID", ""))
    raw_refs = str(row.get("referenced_series_uids", ""))
    refs = [
        x.strip() for x in raw_refs.split(";")
        if x.strip() and x.strip().lower() != "nan"
    ]

    result = {
        "PatientID": patient,
        "SEG_status": row.get("status", ""),
        "SEG_pixel_decode_status": row.get("pixel_decode_status", ""),
        "referenced_series_uids": raw_refs,
        "reference_count": len(refs),
        "matched_CT_UIDs": "",
        "matched_CT_descriptions": "",
        "matched_CT_patient_ids": "",
        "matched_CT_folders": "",
        "matched_CT_folder_exists": "",
        "matched_CT_dicom_file_counts": "",
        "link_status": "",
    }

    matched = []
    for uid in refs:
        matched.extend(ct_index.get(uid, []))

    if not refs:
        result["link_status"] = "NO_REFERENCED_SERIES_UID"
    elif not matched:
        result["link_status"] = "NO_EXACT_CT_UID_MATCH"
    else:
        result["matched_CT_UIDs"] = ";".join(
            str(x.get("SeriesInstanceUID", "")) for x in matched
        )
        result["matched_CT_descriptions"] = ";".join(
            str(x.get("SeriesDescription", "")) for x in matched
        )
        result["matched_CT_patient_ids"] = ";".join(
            str(x.get("PatientID", "")) for x in matched
        )

        folders = []
        exists_values = []
        file_counts = []

        for ct_row in matched:
            folder_value = ct_row.get("S5cmdManifestPath", "")
            folder = Path(str(folder_value)) if pd.notna(folder_value) else None
            folders.append(str(folder) if folder else "")

            exists = bool(folder and folder.is_dir())
            exists_values.append(exists)

            if exists:
                count = sum(
                    1 for p in folder.rglob("*")
                    if p.is_file() and not p.name.lower().endswith(".tmp")
                )
            else:
                count = 0
            file_counts.append(count)

        result["matched_CT_folders"] = ";".join(folders)
        result["matched_CT_folder_exists"] = ";".join(
            str(x) for x in exists_values
        )
        result["matched_CT_dicom_file_counts"] = ";".join(
            str(x) for x in file_counts
        )

        patients_match = all(
            str(x.get("PatientID", "")) == patient for x in matched
        )
        if not patients_match:
            result["link_status"] = "PATIENT_ID_MISMATCH"
        elif not any(exists_values):
            result["link_status"] = "UID_MATCH_FOLDER_MISSING"
        elif not all(exists_values):
            result["link_status"] = "UID_MATCH_PARTIAL_FOLDERS"
        else:
            result["link_status"] = "UID_MATCH_FOLDER_EXISTS"

    results.append(result)

report = pd.DataFrame(results)
destination = out / "hcc_seg_to_ct_linkage.csv"
report.to_csv(destination, index=False)

print("=== SEG-TO-CT LINKAGE SUMMARY ===")
print(report["link_status"].value_counts(dropna=False).to_string())

print("\n=== REFERENCE COUNT SUMMARY ===")
print(report["reference_count"].value_counts(dropna=False).sort_index().to_string())

print("\n=== SAMPLE LINKAGES ===")
print(report[[
    "PatientID", "link_status", "reference_count",
    "matched_CT_descriptions", "matched_CT_patient_ids",
    "matched_CT_folder_exists", "matched_CT_dicom_file_counts"
]].head(15).to_string(index=False))

print("\n=== CASES REQUIRING REVIEW ===")
print(report[~report["link_status"].eq("UID_MATCH_FOLDER_EXISTS")][[
    "PatientID", "link_status", "referenced_series_uids"
]].to_string(index=False))

print("\nReport saved to:", destination)
