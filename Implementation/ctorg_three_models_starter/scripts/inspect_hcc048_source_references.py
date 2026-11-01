import pydicom
from pathlib import Path

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_048")

seg_path = next(
    p for p in base.rglob("*.dcm")
    if getattr(
        pydicom.dcmread(str(p), stop_before_pixels=True, force=True),
        "Modality", ""
    ) == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True, force=True)

print("SEG file:", seg_path.name)
print("Study UID:", getattr(seg, "StudyInstanceUID", "N/A"))
print("Series UID:", getattr(seg, "SeriesInstanceUID", "N/A"))
print("FoR UID:", getattr(seg, "FrameOfReferenceUID", "N/A"))

for tag in [
    "DerivationDescription",
    "SourceImageSequence",
    "ReferencedSeriesSequence",
    "ReferencedImageSequence",
    "StudiesContainingOtherReferencedInstancesSequence",
    "ReferencedStudySequence",
]:
    print(f"\n--- {tag} ---")
    value = getattr(seg, tag, None)
    if value is None:
        print("Not present at top level.")
    else:
        print(value)

print("\n--- Per-frame derivation/source references ---")
found = 0
for i, fg in enumerate(seg.PerFrameFunctionalGroupsSequence, start=1):
    deriv = getattr(fg, "DerivationImageSequence", None)
    if deriv:
        for item in deriv:
            sources = getattr(item, "SourceImageSequence", None)
            if sources:
                for src in sources:
                    found += 1
                    print(
                        "Frame:", i,
                        "SOP UID:", getattr(src, "ReferencedSOPInstanceUID", "N/A"),
                        "Class UID:", getattr(src, "ReferencedSOPClassUID", "N/A"),
                        "Purpose:", getattr(src, "PurposeOfReferenceCodeSequence", "N/A"),
                    )
                    if found >= 20:
                        print("Output limited to first 20 source references.")
                        break
            if found >= 20:
                break
    if found >= 20:
        break

print("\nSource-image references printed:", found)
