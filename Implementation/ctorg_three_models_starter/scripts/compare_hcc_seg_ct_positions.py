from pathlib import Path
from collections import defaultdict
import numpy as np
import pydicom

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
PATIENTS = ("HCC_003", "HCC_019", "HCC_012")

def seq_value(obj, sequence_name, attribute):
    try:
        return np.asarray(
            getattr(getattr(obj, sequence_name)[0], attribute),
            dtype=float
        )
    except Exception:
        return None

for patient in PATIENTS:
    print(f"\n{'='*18} {patient} {'='*18}")
    patient_root = ROOT / patient
    segs, cts = [], []

    for path in patient_root.rglob("*.dcm"):
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True)
            if ds.Modality == "SEG":
                segs.append((path, ds))
            elif ds.Modality == "CT":
                cts.append((path, ds))
        except Exception:
            continue

    if not segs:
        print("No SEG found")
        continue

    # Index CT instances by SOP UID and series.
    ct_by_uid = {}
    series_positions = defaultdict(list)
    for path, ds in cts:
        uid = str(getattr(ds, "SOPInstanceUID", ""))
        series = str(getattr(ds, "SeriesInstanceUID", ""))
        pos = seq_value(ds, "ImagePositionPatient", "__never__")
        try:
            pos = np.asarray(ds.ImagePositionPatient, dtype=float)
        except Exception:
            pos = None
        if uid:
            ct_by_uid[uid] = (ds, pos)
        if pos is not None:
            series_positions[series].append(pos)

    for _, seg in segs:
        frames = getattr(seg, "PerFrameFunctionalGroupsSequence", [])
        shared_orientation = seq_value(
            seg, "PlaneOrientationSequence", "ImageOrientationPatient"
        )
        if shared_orientation is None:
            try:
                shared_orientation = np.asarray(
                    seg.SharedFunctionalGroupsSequence[0]
                    .PlaneOrientationSequence[0].ImageOrientationPatient,
                    dtype=float
                )
            except Exception:
                shared_orientation = None

        rows = []
        missing = 0
        for i, fg in enumerate(frames, start=1):
            try:
                seg_pos = np.asarray(
                    fg.PlanePositionSequence[0].ImagePositionPatient,
                    dtype=float
                )
            except Exception:
                missing += 1
                continue

            segment = None
            try:
                segment = int(
                    fg.SegmentIdentificationSequence[0].ReferencedSegmentNumber
                )
            except Exception:
                pass

            refs = []
            for deriv in getattr(fg, "DerivationImageSequence", []):
                for src in getattr(deriv, "SourceImageSequence", []):
                    uid = str(getattr(src, "ReferencedSOPInstanceUID", ""))
                    if uid:
                        refs.append(uid)

            for uid in refs:
                if uid not in ct_by_uid:
                    rows.append((i, segment, uid, None, None, None))
                    continue

                ct_ds, ct_pos = ct_by_uid[uid]
                if ct_pos is None:
                    continue

                delta = seg_pos - ct_pos
                if shared_orientation is not None:
                    row_dir = shared_orientation[:3]
                    col_dir = shared_orientation[3:]
                    in_plane = np.sqrt(
                        np.dot(delta, row_dir) ** 2 +
                        np.dot(delta, col_dir) ** 2
                    )
                    normal = abs(np.dot(
                        delta, np.cross(row_dir, col_dir)
                    ))
                else:
                    in_plane = np.nan
                    normal = np.nan

                rows.append((
                    i, segment, uid, float(np.linalg.norm(delta)),
                    float(in_plane), float(normal)
                ))

        print("SEG frames:", len(frames), "| missing frame positions:", missing)
        print("Resolved reference rows:", sum(r[3] is not None for r in rows))

        for segment in sorted({r[1] for r in rows if r[1] is not None}):
            subset = [r for r in rows if r[1] == segment and r[3] is not None]
            if not subset:
                continue
            print(
                f"Segment {segment}: references={len(subset)}, "
                f"median_delta={np.median([r[3] for r in subset]):.3f} mm, "
                f"max_delta={max(r[3] for r in subset):.3f} mm, "
                f"max_in_plane={max(r[4] for r in subset):.3f} mm, "
                f"max_normal={max(r[5] for r in subset):.3f} mm"
            )

        print("Largest discrepancies:")
        for r in sorted(
            [r for r in rows if r[3] is not None],
            key=lambda x: x[3], reverse=True
        )[:8]:
            print({
                "frame": r[0], "segment": r[1],
                "reference_uid": r[2],
                "delta_mm": round(r[3], 3),
                "in_plane_mm": round(r[4], 3),
                "normal_mm": round(r[5], 3)
            })
