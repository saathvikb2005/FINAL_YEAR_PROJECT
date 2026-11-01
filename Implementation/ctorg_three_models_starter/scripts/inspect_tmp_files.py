from pathlib import Path
from collections import Counter
import pandas as pd
import pydicom

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg")
audit = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"

tmp_files = [
    p for p in root.rglob("*")
    if p.is_file() and p.name.lower().endswith(".tmp")
]

rows = []
for path in tmp_files:
    row = {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "read_status": "",
        "Modality": "",
        "PatientID": "",
        "SeriesInstanceUID": "",
        "SeriesDescription": "",
    }

    try:
        ds = pydicom.dcmread(
            str(path),
            stop_before_pixels=True,
            force=True,
            specific_tags=[
                "Modality", "PatientID", "SeriesInstanceUID",
                "SeriesDescription", "SOPClassUID"
            ],
        )
        modality = str(getattr(ds, "Modality", "")).strip().upper()
        uid = str(getattr(ds, "SeriesInstanceUID", "")).strip()

        if modality in {"CT", "SEG"} and uid:
            row["read_status"] = "DICOM_HEADER_READABLE"
        else:
            row["read_status"] = "NO_USABLE_CT_SEG_HEADER"

        row["Modality"] = modality
        row["PatientID"] = str(getattr(ds, "PatientID", "")).strip()
        row["SeriesInstanceUID"] = uid
        row["SeriesDescription"] = str(
            getattr(ds, "SeriesDescription", "")
        ).strip()

    except Exception as exc:
        row["read_status"] = "READ_ERROR: " + type(exc).__name__

    rows.append(row)

report = pd.DataFrame(rows)
destination = audit / "hcc_tmp_file_inspection.csv"
report.to_csv(destination, index=False)

print("=== TEMP FILE SUMMARY ===")
print("Temporary files:", len(tmp_files))
if len(report):
    print(report["read_status"].value_counts().to_string())
    print("\n=== MODALITY COUNTS ===")
    print(
        report.loc[
            report["read_status"] == "DICOM_HEADER_READABLE", "Modality"
        ].value_counts(dropna=False).to_string()
    )

    print("\n=== READABLE TEMP FILES ===")
    readable = report[report["read_status"] == "DICOM_HEADER_READABLE"]
    print(readable[[
        "path", "size_bytes", "PatientID", "Modality",
        "SeriesDescription", "SeriesInstanceUID"
    ]].head(20).to_string(index=False))

    print("\n=== FILE SIZE SUMMARY ===")
    print(report["size_bytes"].describe().to_string())

print("\n=== SECOND HCC-TACE-SEG FOLDER ===")
extra = root / "HCC-TACE-Seg"
if extra.exists():
    for path in extra.rglob("*"):
        if path.is_file():
            print(path, "| bytes:", path.stat().st_size)
else:
    print("Folder not found")

print("\nReport saved to:", destination)
