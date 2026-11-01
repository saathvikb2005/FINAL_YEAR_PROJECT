from pathlib import Path
import pandas as pd
import pydicom

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg")
out = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"

seg_csv = out / "hcc_seg_series_candidates.csv"
seg_df = pd.read_csv(seg_csv, low_memory=False)

rows = []

def sequence_items(ds, name):
    try:
        return getattr(ds, name, [])
    except Exception:
        return []

for index, rec in seg_df.iterrows():
    patient = str(rec.get("PatientID", ""))
    folder_value = rec.get("S5cmdManifestPath", "")
    folder = Path(str(folder_value)) if pd.notna(folder_value) else None

    result = {
        "PatientID": patient,
        "SEG_SeriesInstanceUID": rec.get("SeriesInstanceUID", ""),
        "folder": str(folder) if folder else "",
        "dicom_file": "",
        "status": "",
        "error": "",
        "Modality": "",
        "SOPInstanceUID": "",
        "Rows": "",
        "Columns": "",
        "NumberOfFrames": "",
        "segments": "",
        "referenced_series_uids": "",
        "referenced_sop_instance_count": 0,
    }

    if not folder or not folder.exists():
        result["status"] = "FOLDER_MISSING"
        rows.append(result)
        continue

    # Search for DICOM files in this SEG series folder.
    candidates = [
        p for p in folder.rglob("*")
        if p.is_file() and not p.name.lower().endswith(".tmp")
    ]

    found = False
    for file_path in candidates:
        try:
            ds = pydicom.dcmread(
                str(file_path),
                stop_before_pixels=True,
                force=True
            )
            if str(getattr(ds, "Modality", "")).upper() != "SEG":
                continue

            found = True
            result["dicom_file"] = str(file_path)
            result["Modality"] = str(getattr(ds, "Modality", ""))
            result["SOPInstanceUID"] = str(
                getattr(ds, "SOPInstanceUID", "")
            )
            result["Rows"] = getattr(ds, "Rows", "")
            result["Columns"] = getattr(ds, "Columns", "")
            result["NumberOfFrames"] = getattr(ds, "NumberOfFrames", "")

            segments = []
            for item in sequence_items(ds, "SegmentSequence"):
                segments.append({
                    "number": getattr(item, "SegmentNumber", None),
                    "label": getattr(item, "SegmentLabel", None),
                    "algorithm": getattr(item, "SegmentAlgorithmType", None),
                })
            result["segments"] = repr(segments)

            referenced_series = set()
            referenced_instances = set()

            # References can occur in different nested DICOM sequences.
            def walk_references(dataset):
                for elem in dataset:
                    if elem.keyword == "SeriesInstanceUID" and elem.value:
                        referenced_series.add(str(elem.value))
                    elif elem.keyword == "ReferencedSOPInstanceUID" and elem.value:
                        referenced_instances.add(str(elem.value))

                    if elem.VR == "SQ":
                        for child in elem.value:
                            walk_references(child)

            walk_references(ds)
            result["referenced_series_uids"] = ";".join(
                sorted(referenced_series)
            )
            result["referenced_sop_instance_count"] = len(
                referenced_instances
            )
            result["status"] = "READ_OK"
            break

        except Exception as exc:
            result["error"] = repr(exc)

    if not found and not result["status"]:
        result["status"] = (
            "NO_SEG_DICOM_FOUND" if candidates else "NO_FILES_IN_FOLDER"
        )

    rows.append(result)
    if (index + 1) % 10 == 0:
        print(f"Processed {index + 1}/{len(seg_df)} SEG records")

report = pd.DataFrame(rows)
path = out / "hcc_seg_annotation_audit.csv"
report.to_csv(path, index=False)

print("\n=== SEG ANNOTATION AUDIT SUMMARY ===")
print(report["status"].value_counts(dropna=False).to_string())
print("\n=== SAMPLE SEGMENT DEFINITIONS ===")
print(
    report[[
        "PatientID", "status", "Rows", "Columns",
        "NumberOfFrames", "segments",
        "referenced_series_uids",
        "referenced_sop_instance_count"
    ]].head(12).to_string(index=False)
)
print("\nReport saved to:", path)
