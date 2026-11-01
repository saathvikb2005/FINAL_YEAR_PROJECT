from pathlib import Path
from collections import Counter
import pandas as pd
import pydicom

out = Path(
    r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter"
) / "results" / "dataset_audit"

source = pd.read_csv(
    out / "hcc_seg_annotation_audit.csv",
    low_memory=False
)

rows = []

for _, rec in source.iterrows():
    result = {
        "PatientID": rec.get("PatientID", ""),
        "status": "",
        "dicom_file": rec.get("dicom_file", ""),
        "number_of_frames": 0,
        "pixel_array_shape": "",
        "pixel_decode_status": "",
        "segment_definitions": "",
        "frame_counts_by_segment": "",
        "referenced_series_uids": "",
        "referenced_sop_count": 0,
        "error": "",
    }

    file_value = rec.get("dicom_file", "")
    if not isinstance(file_value, str) or not file_value.strip():
        result["status"] = "NO_FILE_PATH"
        rows.append(result)
        continue

    path = Path(file_value)
    if not path.is_file():
        result["status"] = "FILE_MISSING"
        rows.append(result)
        continue

    try:
        ds = pydicom.dcmread(str(path), force=True)
        result["number_of_frames"] = int(
            getattr(ds, "NumberOfFrames", 1)
        )

        definitions = {}
        for seg in getattr(ds, "SegmentSequence", []):
            number = int(seg.SegmentNumber)
            definitions[number] = str(
                getattr(seg, "SegmentLabel", "UNKNOWN")
            )

        result["segment_definitions"] = repr(definitions)

        # Read the referenced series using the specific DICOM sequence.
        series_uids = set()
        sop_uids = set()

        for study in getattr(ds, "ReferencedSeriesSequence", []):
            uid = getattr(study, "SeriesInstanceUID", None)
            if uid:
                series_uids.add(str(uid))

            for instance in getattr(study, "ReferencedInstanceSequence", []):
                sop = getattr(instance, "ReferencedSOPInstanceUID", None)
                if sop:
                    sop_uids.add(str(sop))

        # Also inspect source-image references nested in frame groups.
        for frame in getattr(ds, "PerFrameFunctionalGroupsSequence", []):
            for derivation in getattr(frame, "DerivationImageSequence", []):
                for source_image in getattr(
                    derivation, "SourceImageSequence", []
                ):
                    sop = getattr(
                        source_image, "ReferencedSOPInstanceUID", None
                    )
                    if sop:
                        sop_uids.add(str(sop))

        result["referenced_series_uids"] = ";".join(sorted(series_uids))
        result["referenced_sop_count"] = len(sop_uids)

        # Decode the SEG pixel data and count frames by segment number.
        try:
            pixels = ds.pixel_array
            result["pixel_array_shape"] = str(pixels.shape)
            result["pixel_decode_status"] = "DECODE_OK"

            frame_counts = Counter()
            groups = getattr(ds, "PerFrameFunctionalGroupsSequence", [])

            for i, frame in enumerate(groups):
                segment_number = None
                for identification in getattr(
                    frame, "SegmentIdentificationSequence", []
                ):
                    segment_number = getattr(
                        identification, "ReferencedSegmentNumber", None
                    )
                if segment_number is not None:
                    frame_counts[int(segment_number)] += 1

            result["frame_counts_by_segment"] = repr({
                definitions.get(k, f"Segment_{k}"): v
                for k, v in sorted(frame_counts.items())
            })
        except Exception as exc:
            result["pixel_decode_status"] = "DECODE_ERROR"
            result["error"] = repr(exc)

        result["status"] = "HEADER_OK"

    except Exception as exc:
        result["status"] = "READ_ERROR"
        result["error"] = repr(exc)

    rows.append(result)

report = pd.DataFrame(rows)
destination = out / "hcc_seg_pixel_and_reference_audit.csv"
report.to_csv(destination, index=False)

print("=== SEG PIXEL AND REFERENCE AUDIT ===")
print(report["status"].value_counts(dropna=False).to_string())

print("\n=== PIXEL DECODING ===")
print(report["pixel_decode_status"].value_counts(dropna=False).to_string())

print("\n=== SAMPLE RESULTS ===")
print(report[[
    "PatientID", "status", "number_of_frames",
    "pixel_array_shape", "pixel_decode_status",
    "segment_definitions", "frame_counts_by_segment",
    "referenced_series_uids", "referenced_sop_count", "error"
]].head(12).to_string(index=False))

print("\nReport saved to:", destination)
