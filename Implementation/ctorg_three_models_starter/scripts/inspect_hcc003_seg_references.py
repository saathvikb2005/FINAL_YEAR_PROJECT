import pydicom
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_003")
seg_path = next(
    p for p in base.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
ds = pydicom.dcmread(str(seg_path), stop_before_pixels=True)

print("SEG:", seg_path)
print("\nSEGMENT DEFINITIONS")
for item in ds.SegmentSequence:
    print(
        "Number:", item.SegmentNumber,
        "| Label:", getattr(item, "SegmentLabel", ""),
        "| Description:", getattr(item, "SegmentDescription", ""),
        "| Algorithm:", getattr(item, "SegmentAlgorithmType", "")
    )

print("\nREFERENCED SERIES")
refs = getattr(ds, "ReferencedSeriesSequence", [])
if not refs:
    print("No ReferencedSeriesSequence in top-level SEG metadata.")
for series in refs:
    print("Series UID:", getattr(series, "SeriesInstanceUID", ""))
    print("Referenced images:", len(getattr(series, "ReferencedInstanceSequence", [])))

print("\nFRAME-LEVEL SOURCE REFERENCES")
count = 0
for i, fg in enumerate(ds.PerFrameFunctionalGroupsSequence, start=1):
    deriv = getattr(fg, "DerivationImageSequence", [])
    for item in deriv:
        srcs = getattr(item, "SourceImageSequence", [])
        for src in srcs:
            count += 1
            if count <= 12:
                print(
                    "Frame:", i,
                    "| Source SOP UID:", getattr(src, "ReferencedSOPInstanceUID", ""),
                    "| Source Series UID:",
                    getattr(getattr(src, "PurposeOfReferenceCodeSequence", [None])[0],
                            "CodeMeaning", "")
                )
print("Total frame-level source references:", count)
