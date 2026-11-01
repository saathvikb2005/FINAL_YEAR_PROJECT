from pathlib import Path
import csv
import numpy as np
import pydicom

ROOT = Path(r"D:\FINAL_PROJECT\DATASETS\HCC-TACE-Seg_WSL_CLASSIC\hcc_tace_seg")
PROJECT = Path(r"D:\FINAL_PROJECT\Implementation\ctorg_three_models_starter")
OUT = PROJECT / "results" / "dataset_audit"
PATIENT = "HCC_089"

SEG_PATH = Path(__import__("os").environ["HCC089_SEG_PATH"])

# Explicitly identified candidate series for the July 2005 study.
TARGETS = {
    "RECON2_PRE": "1.3.6.1.4.1.14519.5.2.1.1706.8374.495445119370122224936467178504",
    "RECON2_LIVER_2PHASE": "1.3.6.1.4.1.14519.5.2.1.1706.8374.183102785669372706818207745188",
    "RECON3_LIVER_2PHASE": "1.3.6.1.4.1.14519.5.2.1.1706.8374.187699732728809609459703673419",
}

def vec(ds, key):
    return np.asarray([float(v) for v in getattr(ds, key)], dtype=float)

def orientation(ds):
    iop = vec(ds, "ImageOrientationPatient")
    return iop[:3], iop[3:]

def read_candidates():
    found = {name: [] for name in TARGETS}
    for path in (ROOT / PATIENT).rglob("*"):
        if not path.is_file():
            continue
        try:
            ds = pydicom.dcmread(str(path), stop_before_pixels=True, force=True)
            if str(getattr(ds, "Modality", "")) != "CT":
                continue
            uid = str(getattr(ds, "SeriesInstanceUID", ""))
            for name, target_uid in TARGETS.items():
                if uid == target_uid and all(
                    hasattr(ds, key) for key in
                    ("ImagePositionPatient", "ImageOrientationPatient", "PixelSpacing")
                ):
                    found[name].append({
                        "path": str(path),
                        "sop": str(getattr(ds, "SOPInstanceUID", "")),
                        "for_uid": str(getattr(ds, "FrameOfReferenceUID", "")),
                        "origin": vec(ds, "ImagePositionPatient"),
                        "iop": vec(ds, "ImageOrientationPatient"),
                        "spacing": vec(ds, "PixelSpacing"),
                        "rows": int(ds.Rows),
                        "cols": int(ds.Columns),
                    })
        except Exception:
            continue
    return found

def main():
    if not SEG_PATH.exists():
        raise FileNotFoundError(
            f"SEG file not found at:\n{SEG_PATH}\n"
            "Check the SEG path against the path printed by your earlier scripts."
        )

    OUT.mkdir(parents=True, exist_ok=True)
    seg = pydicom.dcmread(str(SEG_PATH))
    pixels = seg.pixel_array
    shared = seg.SharedFunctionalGroupsSequence[0]
    seg_iop_shared = np.asarray(
        [float(x) for x in shared.PlaneOrientationSequence[0].ImageOrientationPatient]
    )
    seg_spacing_shared = np.asarray(
        [float(x) for x in shared.PixelMeasuresSequence[0].PixelSpacing]
    )
    seg_row_dir = seg_iop_shared[3:]
    seg_col_dir = seg_iop_shared[:3]
    seg_normal = np.cross(seg_col_dir, seg_row_dir)
    seg_for = str(getattr(seg, "FrameOfReferenceUID", ""))

    candidates = read_candidates()
    frame_rows = []

    print(f"SEG frames: {len(seg.PerFrameFunctionalGroupsSequence)}")
    print(f"SEG pixel array: {pixels.shape}")
    print(f"SEG FrameOfReferenceUID: {seg_for}")
    print(f"SEG shared PixelSpacing: {seg_spacing_shared.tolist()}")
    print(f"SEG shared IOP: {seg_iop_shared.tolist()}")

    for name, series in candidates.items():
        print(f"\n{name}: CT images found = {len(series)}")
        if not series:
            continue

        # A CT series should have one consistent orientation and spacing.
        ct0 = series[0]
        ct_col_dir, ct_row_dir = orientation(
            type("DS", (), {"ImageOrientationPatient": ct0["iop"]})()
        )
        ct_normal = np.cross(ct_col_dir, ct_row_dir)
        ct_spacing = ct0["spacing"]
        ct_iop = ct0["iop"]
        ct_for = ct0["for_uid"]

        for item in series:
            item["plane_coord"] = float(np.dot(item["origin"], ct_normal))
        series.sort(key=lambda item: item["plane_coord"])
        plane_coords = np.asarray([item["plane_coord"] for item in series])

        exact_planes = 0
        within_1mm = 0
        all_frame_count = 0
        tumor_frame_count = 0
        tumor_pixels_total = 0
        tumor_pixels_inside = 0
        nonempty_pixels_total = 0
        nonempty_pixels_inside = 0
        max_nearest_plane = 0.0
        plane_distances = []
        inplane_offsets = []

        for frame_idx, fg in enumerate(seg.PerFrameFunctionalGroupsSequence):
            pseq = getattr(fg, "PlanePositionSequence", [])
            if not pseq:
                continue

            seg_origin = np.asarray(
                [float(x) for x in pseq[0].ImagePositionPatient], dtype=float
            )
            seg_iop = seg_iop_shared
            seg_spacing = seg_spacing_shared
            orient_dot = float(np.dot(seg_normal, ct_normal))
            orientation_opposite_or_same = abs(orient_dot)

            # Pick nearest CT plane using the physical plane normal, not Z alone.
            seg_plane_coord = float(np.dot(seg_origin, ct_normal))
            nearest_idx = int(np.argmin(np.abs(plane_coords - seg_plane_coord)))
            ct = series[nearest_idx]
            plane_distance = abs(float(plane_coords[nearest_idx] - seg_plane_coord))

            # SEG origin projected into the CT image's row/column coordinate system.
            delta_origin = seg_origin - ct["origin"]
            origin_col_offset_px = float(np.dot(delta_origin, ct_col_dir) / ct_spacing[1])
            origin_row_offset_px = float(np.dot(delta_origin, ct_row_dir) / ct_spacing[0])
            inplane_offsets.append((origin_row_offset_px, origin_col_offset_px))

            # Compare the SEG's full physical orientation and pixel spacing.
            orientation_match = bool(
                np.allclose(seg_iop[:3], ct_iop[:3], atol=1e-4)
                and np.allclose(seg_iop[3:], ct_iop[3:], atol=1e-4)
            )
            orientation_reversed = bool(
                np.allclose(seg_iop[:3], -ct_iop[:3], atol=1e-4)
                and np.allclose(seg_iop[3:], -ct_iop[3:], atol=1e-4)
            )
            spacing_match = bool(np.allclose(seg_spacing, ct_spacing, atol=1e-4))
            for_match = bool(seg_for and ct_for and seg_for == ct_for)

            # Transform every foreground SEG pixel to the nearest CT image grid.
            mask = pixels[frame_idx]
            rr, cc = np.where(mask > 0)
            n_pixels = int(len(rr))
            seg_number_seq = getattr(fg, "SegmentIdentificationSequence", [])
            seg_number = (
                int(seg_number_seq[0].ReferencedSegmentNumber)
                if seg_number_seq else -1
            )
            is_tumor = seg_number == 2 and n_pixels > 0

            if n_pixels:
                xyz = (
                    seg_origin[None, :]
                    + rr[:, None] * seg_spacing[0] * seg_row_dir[None, :]
                    + cc[:, None] * seg_spacing[1] * seg_col_dir[None, :]
                )
                delta = xyz - ct["origin"][None, :]
                ct_rows = delta @ ct_row_dir / ct_spacing[0]
                ct_cols = delta @ ct_col_dir / ct_spacing[1]

                inside = (
                    (ct_rows >= -0.5) & (ct_rows < ct["rows"] - 0.5)
                    & (ct_cols >= -0.5) & (ct_cols < ct["cols"] - 0.5)
                )
                n_inside = int(inside.sum())
                inplane_error_row = float(np.median(ct_rows - rr))
                inplane_error_col = float(np.median(ct_cols - cc))
                nonempty_pixels_total += n_pixels
                nonempty_pixels_inside += n_inside
                if is_tumor:
                    tumor_pixels_total += n_pixels
                    tumor_pixels_inside += n_inside
            else:
                n_inside = 0
                inplane_error_row = float("nan")
                inplane_error_col = float("nan")

            exact = plane_distance < 0.01
            within_one = plane_distance <= 1.0
            all_frame_count += 1
            exact_planes += int(exact)
            within_1mm += int(within_one)
            max_nearest_plane = max(max_nearest_plane, plane_distance)
            plane_distances.append(plane_distance)
            tumor_frame_count += int(is_tumor)

            frame_rows.append({
                "patient": PATIENT,
                "candidate_series": name,
                "candidate_series_uid": TARGETS[name],
                "seg_frame": frame_idx + 1,
                "segment_number": seg_number,
                "is_tumor_positive": is_tumor,
                "seg_foreground_pixels": n_pixels,
                "pixels_inside_nearest_ct_grid": n_inside,
                "inside_fraction": (n_inside / n_pixels) if n_pixels else "",
                "seg_z_mm": float(seg_origin[2]),
                "seg_plane_coord_mm": seg_plane_coord,
                "nearest_ct_plane_distance_mm": plane_distance,
                "nearest_ct_sop_uid": ct["sop"],
                "nearest_ct_path": ct["path"],
                "frame_of_reference_match": for_match,
                "orientation_match": orientation_match,
                "orientation_reversed": orientation_reversed,
                "orientation_abs_normal_dot": orientation_opposite_or_same,
                "pixel_spacing_match": spacing_match,
                "seg_pixel_spacing": str(seg_spacing.tolist()),
                "ct_pixel_spacing": str(ct_spacing.tolist()),
                "seg_origin_row_offset_px": origin_row_offset_px,
                "seg_origin_col_offset_px": origin_col_offset_px,
                "median_mapped_row_minus_seg_row_px": inplane_error_row,
                "median_mapped_col_minus_seg_col_px": inplane_error_col,
                "ct_frame_of_reference_uid": ct_for,
            })

        tumor_rows = [
            r for r in frame_rows
            if r["candidate_series"] == name and r["is_tumor_positive"]
        ]
        tumor_distances = [r["nearest_ct_plane_distance_mm"] for r in tumor_rows]
        tumor_inside_pixels = sum(r["pixels_inside_nearest_ct_grid"] for r in tumor_rows)
        tumor_total_pixels = sum(r["seg_foreground_pixels"] for r in tumor_rows)

        print(f"  CT FrameOfReferenceUID match: {ct_for == seg_for}")
        print(f"  Orientation exact match: {np.allclose(seg_iop, ct_iop, atol=1e-4)}")
        print(f"  Orientation reversed (both axes): {np.allclose(seg_iop, -ct_iop, atol=1e-4)}")
        print(f"  Pixel spacing match: {np.allclose(seg_spacing_shared, ct_spacing, atol=1e-4)}")
        print(f"  Frames evaluated: {all_frame_count}")
        print(f"  Frames with exact plane match (<0.01 mm): {exact_planes}/{all_frame_count}")
        print(f"  Frames within 1 mm plane distance: {within_1mm}/{all_frame_count}")
        print(f"  Max / mean nearest plane distance: {max_nearest_plane:.3f} / {np.mean(plane_distances):.3f} mm")
        print(f"  Nonempty tumor frames: {tumor_frame_count}")
        if tumor_distances:
            print(f"  Tumor frames exact plane match: {sum(d < 0.01 for d in tumor_distances)}/{len(tumor_distances)}")
            print(f"  Tumor frames within 1 mm: {sum(d <= 1.0 for d in tumor_distances)}/{len(tumor_distances)}")
            print(f"  Tumor pixels inside nearest CT grid: {tumor_inside_pixels}/{tumor_total_pixels} "
                  f"({100*tumor_inside_pixels/tumor_total_pixels:.2f}%)")
        print(f"  All nonempty mask pixels inside nearest CT grid: "
              f"{nonempty_pixels_inside}/{nonempty_pixels_total} "
              f"({100*nonempty_pixels_inside/nonempty_pixels_total:.2f}%)" if nonempty_pixels_total else
              "  No nonempty masks found")

    frame_csv = OUT / "hcc089_full_physical_geometry_by_frame.csv"
    summary_csv = OUT / "hcc089_full_physical_geometry_summary.csv"
    if frame_rows:
        with frame_csv.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(frame_rows[0].keys()))
            writer.writeheader()
            writer.writerows(frame_rows)

        summary_rows = []
        for name in TARGETS:
            rows = [r for r in frame_rows if r["candidate_series"] == name]
            if not rows:
                continue
            tumor = [r for r in rows if r["is_tumor_positive"]]
            nonempty = [r for r in rows if r["seg_foreground_pixels"] > 0]
            summary_rows.append({
                "candidate_series": name,
                "candidate_series_uid": TARGETS[name],
                "frames_evaluated": len(rows),
                "frames_exact_plane_match": sum(r["nearest_ct_plane_distance_mm"] < 0.01 for r in rows),
                "frames_within_1mm": sum(r["nearest_ct_plane_distance_mm"] <= 1.0 for r in rows),
                "mean_nearest_plane_distance_mm": np.mean([r["nearest_ct_plane_distance_mm"] for r in rows]),
                "max_nearest_plane_distance_mm": max(r["nearest_ct_plane_distance_mm"] for r in rows),
                "tumor_positive_frames": len(tumor),
                "tumor_frames_exact_plane_match": sum(r["nearest_ct_plane_distance_mm"] < 0.01 for r in tumor),
                "tumor_frames_within_1mm": sum(r["nearest_ct_plane_distance_mm"] <= 1.0 for r in tumor),
                "tumor_pixel_total": sum(r["seg_foreground_pixels"] for r in tumor),
                "tumor_pixels_inside_ct_grid": sum(r["pixels_inside_nearest_ct_grid"] for r in tumor),
                "nonempty_frames": len(nonempty),
                "nonempty_pixel_total": sum(r["seg_foreground_pixels"] for r in nonempty),
                "nonempty_pixels_inside_ct_grid": sum(r["pixels_inside_nearest_ct_grid"] for r in nonempty),
                "frame_of_reference_match": rows[0]["frame_of_reference_match"],
                "orientation_match": rows[0]["orientation_match"],
                "orientation_reversed": rows[0]["orientation_reversed"],
                "pixel_spacing_match": rows[0]["pixel_spacing_match"],
            })
        with summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
            writer.writeheader()
            writer.writerows(summary_rows)

        print("\nSaved new files:")
        print(frame_csv)
        print(summary_csv)
    else:
        print("No frame results produced. Check the SEG path and candidate series UIDs.")

if __name__ == "__main__":
    main()

