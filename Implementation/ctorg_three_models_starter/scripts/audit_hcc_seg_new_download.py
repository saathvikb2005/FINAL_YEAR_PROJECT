from pathlib import Path
from collections import Counter
import pandas as pd
import pydicom

root = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
out = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter\results\dataset_audit")
out.mkdir(parents=True, exist_ok=True)

rows = []

seg_files = []
for path in root.rglob("*.dcm"):
    try:
        ds = pydicom.dcmread(
            str(path), stop_before_pixels=True, force=True,
            specific_tags=["Modality"]
        )
        if str(getattr(ds, "Modality", "")).strip().upper() == "SEG":
            seg_files.append(path)
    except Exception:
        pass

print("SEG files discovered:", len(seg_files))
print("Starting pixel decoding and reference audit...")

for index, path in enumerate(sorted(seg_files), start=1):
    row = {
        "PatientID": "",
        "path": str(path),
        "SeriesInstanceUID": "",
        "referenced_series_uids": "",
        "number_of_frames": 0,
        "pixel_array_shape": "",
        "pixel_decode_status": "",
        "segments": "",
        "frame_counts_by_segment": "",
        "tumor_mass_segment_present": False,
        "error": "",
    }

    try:
        ds = pydicom.dcmread(str(path), force=True)

        row["PatientID"] = str(getattr(ds, "PatientID", "")).strip()
        row["SeriesInstanceUID"] = str(
            getattr(ds, "SeriesInstanceUID", "")
        ).strip()
        row["number_of_frames"] = int(
            getattr(ds, "NumberOfFrames", 1)
        )

        definitions = {}
        for seg in getattr(ds, "SegmentSequence", []):
            number = int(seg.SegmentNumber)
            label = str(getattr(seg, "SegmentLabel", "UNKNOWN"))
            description = str(
                getattr(
                    getattr(seg, "SegmentedPropertyTypeCodeSequence", [None])[0],
                    "CodeMeaning", ""
                )
            )
            definitions[number] = {
                "label": label,
                "description": description,
            }

        row["segments"] = repr(definitions)
        row["tumor_mass_segment_present"] = any(
            "mass" in v["label"].lower()
            or "tumor" in v["label"].lower()
            or "lesion" in v["label"].lower()
            for v in definitions.values()
        )

        refs = set()
        for item in getattr(ds, "ReferencedSeriesSequence", []):
            uid = getattr(item, "SeriesInstanceUID", None)
            if uid:
                refs.add(str(uid))

        # Some SEG objects expose source references through frame groups.
        for frame in getattr(ds, "PerFrameFunctionalGroupsSequence", []):
            for derivation in getattr(frame, "DerivationImageSequence", []):
                for source in getattr(derivation, "SourceImageSequence", []):
                    # ReferencedSOPInstanceUID identifies an image instance;
                    # it is not itself a SeriesInstanceUID.
                    pass

        row["referenced_series_uids"] = ";".join(sorted(refs))

        try:
            pixels = ds.pixel_array
            row["pixel_array_shape"] = str(pixels.shape)
            row["pixel_decode_status"] = "DECODE_OK"

            counts = Counter()
            groups = getattr(ds, "PerFrameFunctionalGroupsSequence", [])
            for frame in groups:
                for identification in getattr(
                    frame, "SegmentIdentificationSequence", []
                ):
                    number = getattr(
                        identification, "ReferencedSegmentNumber", None
                    )
                    if number is not None:
                        counts[int(number)] += 1

            row["frame_counts_by_segment"] = repr({
                definitions.get(k, {}).get("label", f"Segment_{k}"): v
                for k, v in sorted(counts.items())
            })

            if pixels.shape[0] != row["number_of_frames"] and pixels.ndim >= 3:
                row["error"] = (
                    f"Pixel frame dimension {pixels.shape[0]} does not match "
                    f"NumberOfFrames {row['number_of_frames']}"
                )
        except Exception as exc:
            row["pixel_decode_status"] = "DECODE_ERROR"
            row["error"] = repr(exc)

    except Exception as exc:
        row["pixel_decode_status"] = "READ_ERROR"
        row["error"] = repr(exc)

    rows.append(row)

    if index % 10 == 0 or index == len(seg_files):
        print(f"Processed {index}/{len(seg_files)} SEG files")

report = pd.DataFrame(rows)
destination = out / "hcc_seg_pixel_reference_audit_new_download.csv"
report.to_csv(destination, index=False)

print("\n=== SEG VALIDATION SUMMARY ===")
print("SEG files audited:", len(report))
print("\nPixel decoding:")
print(report["pixel_decode_status"].value_counts(dropna=False).to_string())
print("\nTumor/Mass/L lesion-like segment label present:")
print(report["tumor_mass_segment_present"].value_counts(dropna=False).to_string())
print("\nSEG objects with CT series references:", int(
    report["referenced_series_uids"].fillna("").str.strip().ne("").sum()
))
print("\nUnique patients in SEG files:", report["PatientID"].nunique())
print("\nErrors:")
errors = report[report["error"].fillna("").str.strip().ne("")]
print(errors[["PatientID", "path", "pixel_decode_status", "error"]].head(20).to_string(index=False) if not errors.empty else "None")
print("\nReport saved to:", destination)
