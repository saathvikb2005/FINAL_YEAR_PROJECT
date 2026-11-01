import pydicom
from pathlib import Path
from collections import Counter

base = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg\HCC_003")
target_uid = "1.3.6.1.4.1.14519.5.2.1.1706.8374.281650679207816520863173918688"

seg_path = next(
    p for p in base.rglob("*.dcm")
    if pydicom.dcmread(str(p), stop_before_pixels=True, force=True).Modality == "SEG"
)
seg = pydicom.dcmread(str(seg_path), stop_before_pixels=True)

# Build local CT index.
local_ct = {}
for p in base.rglob("*.dcm"):
    try:
        d = pydicom.dcmread(str(p), stop_before_pixels=True, force=True)
        if getattr(d, "Modality", "") == "CT":
            local_ct[str(d.SOPInstanceUID)] = {
                "path": str(p),
                "series": str(d.SeriesInstanceUID),
                "z": float(d.ImagePositionPatient[2]),
            }
    except Exception:
        continue

print("Local CT SOP count:", len(local_ct))

referenced = []
frame_records = []

for frame_no, fg in enumerate(seg.PerFrameFunctionalGroupsSequence, start=1):
    seg_no = int(fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber)
    z = float(fg.PlanePositionSequence[0].ImagePositionPatient[2])

    deriv = getattr(fg, "DerivationImageSequence", [])
    frame_refs = []
    for item in deriv:
        for src in getattr(item, "SourceImageSequence", []):
            sop = str(getattr(src, "ReferencedSOPInstanceUID", ""))
            if sop:
                referenced.append(sop)
                frame_refs.append(sop)

    frame_records.append((frame_no, seg_no, z, frame_refs))

unique_refs = set(referenced)
resolved = unique_refs & set(local_ct)
missing = unique_refs - set(local_ct)

print("Reference entries:", len(referenced))
print("Unique referenced SOPs:", len(unique_refs))
print("Resolved locally:", len(resolved))
print("Missing locally:", len(missing))

resolved_series_counts = Counter(local_ct[s]["series"] for s in resolved)
print("\nResolved references by local CT series:")
for series, count in resolved_series_counts.most_common():
    print(count, "|", series, "| target AP series:", series == target_uid)

print("\nFirst 15 unresolved references:")
for sop in sorted(missing)[:15]:
    print(sop)

print("\nPer-segment frame reference summary:")
for seg_no in sorted(set(r[1] for r in frame_records)):
    rows = [r for r in frame_records if r[1] == seg_no]
    n_frames = sum(bool(r[3]) for r in rows)
    frame_ref_uids = {s for r in rows for s in r[3]}
    resolved_here = sum(s in local_ct for s in frame_ref_uids)
    target_here = sum(
        1 for s in frame_ref_uids
        if s in local_ct and local_ct[s]["series"] == target_uid
    )
    print(
        f"Segment {seg_no}: frames={len(rows)}, "
        f"frames_with_refs={n_frames}, unique_source_SOPs={len(frame_ref_uids)}, "
        f"resolved={resolved_here}, in_target_AP_series={target_here}"
    )

print("\nExamples: first 10 frames with their source image Z positions")
for frame_no, seg_no, z, refs in frame_records:
    if refs:
        mapped = [
            (local_ct[s]["series"], local_ct[s]["z"])
            for s in refs if s in local_ct
        ]
        print(
            f"Frame {frame_no}, segment {seg_no}, SEG Z={z:.2f}, "
            f"resolved source positions={mapped[:4]}"
        )
    if frame_no >= 10:
        break
