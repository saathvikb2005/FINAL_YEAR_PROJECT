# FINAL_PROJECT file inventory

## Scope and reading guide

This document describes the files present under `D:\FINAL_PROJECT` as of
2026-11-01. It records each file's location, type, name/pattern, purpose, and
contents. Files that are repeated data instances (for example, thousands of
DICOM slices, generated overlays, and files inside the local Python virtual
environment) are represented by an exhaustive deterministic pattern and a
count rather than by repeating the same description thousands of times.

The GitHub repository contains the project documentation, implementation, and
analysis outputs. The medical-imaging data under `DATASETS/` and the local
Python environment under `Implementation/ctorg_three_models_starter/.venv/`
are intentionally excluded from version control by the root `.gitignore`.
They must be obtained or created locally before running data-dependent work.

The current recursive scan found **62,845 files**:

| Area | Files | Main contents |
|---|---:|---|
| `DATASETS/` | 52,251 | CT-ORG and HCC-TACE DICOM data, NIfTI labels, and metadata |
| `Implementation/ctorg_three_models_starter/` | 10,573 | Python implementation, analysis scripts, results, and `.venv` |
| `Docs/` | 14 | Research and project-status documents |
| Project root | 6 | TCIA download/help, command logs, and this inventory |

The scan reported these important file types: 52,079 `.dcm`, 4,070 `.py`,
3,987 `.pyc`, 402 `.pyi`, 295 `.gz`, 264 `.png`, and 104 `.csv` files. The
local virtual environment accounts for most of the Python, bytecode, stub, and
third-party package files. These files are present in the working tree for
local execution but are not part of the GitHub repository.

## Project root

| Location | Type | Name | What it does / contains |
|---|---|---|---|
| `D:\FINAL_PROJECT\HCC-TACE-Seg_resume.log` | Log text | `HCC-TACE-Seg_resume.log` | Resume/progress log from the HCC-TACE dataset acquisition or processing workflow. Contains timestamped status, restart, and recovery messages. |
| `D:\FINAL_PROJECT\TCIA_help.txt` | Plain text | `TCIA_help.txt` | Help/reference output for the TCIA command-line tooling. Contains command usage and operational guidance. |
| `D:\FINAL_PROJECT\tcia_cli_stderr.txt` | Plain text log | `tcia_cli_stderr.txt` | Standard-error capture from a TCIA CLI run. Contains warnings, errors, and diagnostic messages. |
| `D:\FINAL_PROJECT\tcia_cli_stdout.txt` | Plain text log | `tcia_cli_stdout.txt` | Standard-output capture from a TCIA CLI run. Contains normal command progress and results. |
| `D:\FINAL_PROJECT\tcia_download_stderr.txt` | Plain text log | `tcia_download_stderr.txt` | Standard-error capture from the TCIA download process. Contains download warnings and failures. |
| `D:\FINAL_PROJECT\tcia_download_stdout.txt` | Plain text log | `tcia_download_stdout.txt` | Standard-output capture from the TCIA download process. Contains download progress and completion information. |

## `Docs/`

| Location | Type | Name | What it does / contains |
|---|---|---|---|
| `Docs/1.CTORG_HCC_TACE_Research_Progress_Report.docx` | Microsoft Word document | Research progress report | Formal research progress report covering CT-ORG, HCC, and TACE work completed to the report date. |
| `Docs/2.CTORG_HCC_TACE_Phase1_Phase2_Progress_Report.docx` | Microsoft Word document | Phase 1/Phase 2 progress report | Consolidates progress, findings, and remaining work across the first two project phases. |
| `Docs/3.CTORG_HCC_TACE_Consolidated_Project_Status_2026-10-17.docx` | Microsoft Word document | Consolidated project status | Dated status report combining the latest implementation, data-quality, and research state. |
| `Docs/3.CTORG_HCC_TACE_Phase2_Decision_Note_2026-10-17.md` | Markdown | Phase 2 decision note | Human-readable decision record for Phase 2, including conclusions, rationale, and next actions. |
| `Docs/4.HCC_012_FrameOfReference_Investigation_2026-10-17.md` | Markdown | HCC-012 frame-of-reference investigation | Investigation of DICOM frame-of-reference and spatial-registration behavior for HCC-012. |
| `Docs/5.HCC_024_Geometry_Investigation_2026-10-17.md` | Markdown | HCC-024 geometry investigation | Investigation of CT/segmentation geometry alignment and related findings for HCC-024. |
| `Docs/5.HCC_003_Spatial_Provenance_Investigation_2026-10-17.md` | Markdown | HCC-003 spatial-provenance investigation | Investigation of HCC-003 source-image provenance, spatial references, and segmentation-to-CT relationships. |
| `Docs/6.HCC_Mixed_Source_Reference_Geometry_Investigation_2026-10-17.md` | Markdown | Mixed-source reference-geometry investigation | Investigation of cases where segmentation references and geometric CT candidates come from mixed sources. |
| `Docs/7.HCC_019_Source_Series_Investigation_2026-10-17.md` | Markdown | HCC-019 source-series investigation | Investigation of HCC-019 source-series selection and its effect on segmentation linkage and geometry. |
| `Docs/8.HCC_024_028_043_OneMillimeter_Offset_Investigation_2026-10-17.md` | Markdown | One-millimeter offset investigation | Investigation of approximately one-millimeter spatial offsets in HCC-024, HCC-028, and HCC-043. |
| `Docs/9.HCC_015_016_Systematic_Offset_Investigation_2026-10-17.md` | Markdown | HCC-015/HCC-016 systematic-offset investigation | Investigation of systematic coordinate or geometry offsets for HCC-015 and HCC-016. |
| `Docs/10.HCC_089_Declared_Source_vs_Geometric_Candidate_2026-10-17.md` | Markdown | HCC-089 source/candidate comparison | Compares the declared DICOM source series with the geometrically best candidate for HCC-089. |
| `Docs/11.CTORG_HCC_TACE_Phase2_Addendum_2026-10-18.md` | Markdown | Phase 2 addendum | Adds findings, decisions, and updates produced after the Phase 2 status and decision documents. |
| `Docs/12.CTORG_HCC_TACE_Phase2_Closure_Report_2026-10-18.md` | Markdown | Phase 2 closure report | Records Phase 2 completion status, final findings, unresolved items, and closure decisions. |

## `DATASETS/CT-ORG/`

### CT-ORG package metadata and labels

| Location | Type | Name/pattern | What it does / contains |
|---|---|---|---|
| `DATASETS/CT-ORG/PKG - CT-ORG/CT-ORG.sums` | Checksum/manifest text | `CT-ORG.sums` | Package checksum or integrity manifest for the CT-ORG distribution. |
| `DATASETS/CT-ORG/PKG - CT-ORG/CT-ORG/OrganSegmentations/README.txt` | Plain text | `README.txt` | Dataset-specific instructions and description for the organ-segmentation package. |
| `DATASETS/CT-ORG/PKG - CT-ORG/CT-ORG/OrganSegmentations/labels-0.nii.gz` through `labels-115.nii.gz` | GZip-compressed NIfTI | `labels-0.nii.gz` ... `labels-115.nii.gz` | 116 volumetric organ-label masks. Each file contains voxel-wise segmentation labels for one CT-ORG case/volume. |

### CT-ORG DICOM files

The CT-ORG package also contains DICOM image files under its dataset
subdirectories. Every file matching:

`DATASETS/CT-ORG/PKG - CT-ORG/CT-ORG/**/*.dcm`

is a medical-imaging DICOM object containing CT pixel data plus acquisition,
patient/study/series identifiers, orientation, spacing, and slice-position
metadata. These are source images used with the NIfTI organ labels.

## `DATASETS/HCC-TACE-Seg_WSL_CLASSIC/`

### Patient folders

The directory contains `hcc_tace_seg/` with patient folders
`HCC_001/` through `HCC_105/`. The patient-folder structure is:

`DATASETS/HCC-TACE-Seg_WSL_CLASSIC/hcc_tace_seg/HCC_NNN/`

where `NNN` is the zero-padded patient number from `001` to `105`.

Each patient folder contains the downloaded HCC/TACE imaging and segmentation
objects. Every file matching:

`DATASETS/HCC-TACE-Seg_WSL_CLASSIC/hcc_tace_seg/HCC_[001-105]/**/*.dcm`

is a DICOM object. Depending on the patient and series, it represents one CT
image slice, a DICOM segmentation object, or related imaging metadata. The
files contain pixel data and DICOM tags used by the audit scripts to link
segmentations to CT series, compare geometry, and verify frame-of-reference
and coordinate mappings. The HCC dataset contributes the majority of the
project's 51,968 dataset DICOM files.

The exact concrete paths are all files below those 105 patient directories;
the patient number is the only variable component. Files are intentionally
described as a pattern because individual DICOM filenames are generated UIDs
and do not communicate a meaningful human-readable role.

### HCC metadata

| Location | Type | Name | What it does / contains |
|---|---|---|---|
| `DATASETS/HCC-TACE-Seg_WSL_CLASSIC/metadata/metadata.csv` | CSV | `metadata.csv` | Dataset metadata table used to identify HCC patients, studies, series, and acquisition information. It supports local-file inventory, reconciliation, and download/audit checks. |

## `Implementation/ctorg_three_models_starter/`

This directory is the executable research implementation. It contains model
code, analysis/quality-control scripts, generated results, documentation, and
the local Python environment used to run the work.

### Top-level documentation

| Location | Type | Name | What it does / contains |
|---|---|---|---|
| `Implementation/ctorg_three_models_starter/README.md` | Markdown | `README.md` | Main implementation README. Describes setup, project purpose, execution, and expected outputs. |
| `Implementation/ctorg_three_models_starter/README_phase2_updated.md` | Markdown | `README_phase2_updated.md` | Phase 2 update to the implementation README, documenting newer workflows, findings, and usage changes. |

### Source models

| Location | Type | Name | What it does / contains |
|---|---|---|---|
| `Implementation/ctorg_three_models_starter/src/models/unet3d.py` | Python | `unet3d.py` | Defines the 3D U-Net neural-network architecture and its building blocks for volumetric medical-image segmentation. |
| `Implementation/ctorg_three_models_starter/src/models/three_models.py` | Python | `three_models.py` | Defines or coordinates the three model variants used by the starter implementation and exposes model-construction/training-related logic. |

### `scripts/` analysis and validation programs

All files in this directory are Python scripts. They read DICOM/NIfTI data,
metadata, and prior result tables; perform audits, spatial calculations,
linkage checks, visualizations, or model tests; and write tables, logs, and
overlays into `results/`. The following is the complete 82-file script list.

| Location | File name | Purpose and contents |
|---|---|---|
| `scripts/` | `audit_datasets.py` | Audits dataset structure and completeness. |
| `scripts/` | `audit_hcc003_frame_order.py` | Audits HCC-003 segmentation frame ordering. |
| `scripts/` | `audit_hcc048_recon3_mapping_qc_run1.py` | Runs HCC-048 reconstruction-3 mapping quality control. |
| `scripts/` | `audit_hcc048_tumor_inplane_projection.py` | Audits HCC-048 tumor in-plane projection. |
| `scripts/` | `audit_hcc089_seg_frame_structure.py` | Audits HCC-089 segmentation frame structure. |
| `scripts/` | `audit_hcc_ct_seg_geometry_alignment.py` | Compares CT and segmentation geometry. |
| `scripts/` | `audit_hcc_ct_seg_linkage_new_download.py` | Audits CT/SEG linkage for the new download. |
| `scripts/` | `audit_hcc_dicom_coverage_new_download.py` | Audits DICOM coverage for the new download. |
| `scripts/` | `audit_hcc_frame_reference_geometry.py` | Audits frame-reference geometry. |
| `scripts/` | `audit_hcc_seg_geometry_v2.py` | Second-version segmentation geometry audit. |
| `scripts/` | `audit_hcc_seg_geometry_v3_review.py` | Third-version geometry review audit. |
| `scripts/` | `audit_hcc_seg_new_download.py` | Audits newly downloaded segmentations. |
| `scripts/` | `audit_hcc_seg_pixels.py` | Audits segmentation pixel encodings and values. |
| `scripts/` | `audit_hcc_series.py` | Audits HCC series organization and metadata. |
| `scripts/` | `audit_hcc_series_new_download.py` | Audits series from the new download. |
| `scripts/` | `build_hcc_patient_review_table.py` | Builds a patient-level review table. |
| `scripts/` | `check_hcc003_segment_origins.py` | Checks HCC-003 segment origins. |
| `scripts/` | `check_hcc003_tumor_pixel_mapping.py` | Checks HCC-003 tumor pixel mapping. |
| `scripts/` | `check_hcc048_inplane_offset.py` | Checks HCC-048 in-plane offsets. |
| `scripts/` | `check_hcc_seg_ct_pixel_mapping.py` | Checks CT-to-segmentation pixel mapping. |
| `scripts/` | `check_hcc_whole_root.py` | Checks the complete HCC dataset root. |
| `scripts/` | `check_local_ct_uids.py` | Checks locally available CT UIDs. |
| `scripts/` | `check_local_ct_uids_new_download.py` | Checks CT UIDs from the new download. |
| `scripts/` | `compare_hcc003_liver_mass_masks.py` | Compares HCC-003 liver and mass masks. |
| `scripts/` | `compare_hcc003_liver_tumor_slices.py` | Compares HCC-003 liver/tumor slice selections. |
| `scripts/` | `compare_hcc048_all_slice_geometry.py` | Compares all HCC-048 slice geometry. |
| `scripts/` | `compare_hcc048_ct_candidates.py` | Compares candidate HCC-048 CT series. |
| `scripts/` | `compare_hcc_local_coverage.py` | Compares local HCC coverage. |
| `scripts/` | `compare_hcc_seg_ct_positions.py` | Compares CT and segmentation positions. |
| `scripts/` | `create_hcc003_ap_coordinate_overlays.py` | Creates HCC-003 anterior-posterior coordinate overlays. |
| `scripts/` | `create_hcc015_016_tumor_qc_run1.py` | Creates tumor QC outputs for HCC-015 and HCC-016. |
| `scripts/` | `create_hcc048_physical_overlays.py` | Creates HCC-048 physical-coordinate overlays. |
| `scripts/` | `create_hcc089_physical_overlays.py` | Creates HCC-089 physical-coordinate overlays. |
| `scripts/` | `create_hcc089_recon2_pre_overlays.py` | Creates pre-review reconstruction-2 overlays for HCC-089. |
| `scripts/` | `create_hcc_tumor_overlays.py` | Creates general HCC tumor overlays. |
| `scripts/` | `diagnose_hcc019_frame_offsets.py` | Diagnoses HCC-019 frame offsets. |
| `scripts/` | `diagnose_hcc048_offset.py` | Diagnoses HCC-048 offset issues. |
| `scripts/` | `diagnose_hcc089_full_geometry.py` | Diagnoses full HCC-089 geometry. |
| `scripts/` | `diagnose_hcc_physical_geometry.py` | Diagnoses physical-coordinate geometry issues. |
| `scripts/` | `inspect_ctorg_labels.py` | Inspects CT-ORG labels. |
| `scripts/` | `inspect_hcc003_coordinate_candidates.py` | Inspects HCC-003 coordinate candidates. |
| `scripts/` | `inspect_hcc003_mapping_geometry.py` | Inspects HCC-003 mapping geometry. |
| `scripts/` | `inspect_hcc003_seg_geometry.py` | Inspects HCC-003 segmentation geometry. |
| `scripts/` | `inspect_hcc003_seg_references.py` | Inspects HCC-003 segmentation references. |
| `scripts/` | `inspect_hcc003_series.py` | Inspects HCC-003 series. |
| `scripts/` | `inspect_hcc019_dimension_indices.py` | Inspects HCC-019 dimension indices. |
| `scripts/` | `inspect_hcc019_mask_bounds.py` | Inspects HCC-019 mask bounds. |
| `scripts/` | `inspect_hcc019_origins.py` | Inspects HCC-019 image origins. |
| `scripts/` | `inspect_hcc019_provenance.py` | Inspects HCC-019 provenance. |
| `scripts/` | `inspect_hcc019_spatial_metadata.py` | Inspects HCC-019 spatial metadata. |
| `scripts/` | `inspect_hcc048_hcc089_ct_geometry.py` | Inspects CT geometry for HCC-048 and HCC-089. |
| `scripts/` | `inspect_hcc048_recon3_alignment.py` | Inspects HCC-048 reconstruction-3 alignment. |
| `scripts/` | `inspect_hcc048_seg_frame_refs.py` | Inspects HCC-048 segmentation frame references. |
| `scripts/` | `inspect_hcc048_seg_geometry.py` | Inspects HCC-048 segmentation geometry. |
| `scripts/` | `inspect_hcc048_seg_metadata.py` | Inspects HCC-048 segmentation metadata. |
| `scripts/` | `inspect_hcc048_selected_ct.py` | Inspects the selected HCC-048 CT series. |
| `scripts/` | `inspect_hcc048_source_references.py` | Inspects HCC-048 source references. |
| `scripts/` | `inspect_hcc089_seg_references.py` | Inspects HCC-089 segmentation references. |
| `scripts/` | `inspect_hcc_geometry_cases.py` | Inspects selected HCC geometry cases. |
| `scripts/` | `inspect_hcc_metadata.py` | Inspects HCC metadata. |
| `scripts/` | `inspect_hcc_seg.py` | Inspects HCC segmentation objects. |
| `scripts/` | `inspect_hcc_tumor_pixels.py` | Inspects tumor pixel data. |
| `scripts/` | `inspect_seg_frame_positions.py` | Inspects segmentation frame positions. |
| `scripts/` | `inspect_tmp_files.py` | Inspects temporary files. |
| `scripts/` | `inventory_hcc003_series.py` | Inventories HCC-003 series. |
| `scripts/` | `link_hcc_seg_to_ct.py` | Links HCC segmentation objects to CT series. |
| `scripts/` | `list_hcc048_tumor_frames.py` | Lists HCC-048 tumor frames. |
| `scripts/` | `list_hcc089_tumor_frames.py` | Lists HCC-089 tumor frames. |
| `scripts/` | `map_hcc089_tumor_to_ct.py` | Maps HCC-089 tumor data to CT slices. |
| `scripts/` | `project_hcc003_seg_corners.py` | Projects HCC-003 segmentation corners. |
| `scripts/` | `summarize_ctorg_labels.py` | Summarizes CT-ORG label distributions. |
| `scripts/` | `test_models.py` | Exercises/tests the three model implementations. |
| `scripts/` | `validate_hcc003_common_grid_run1.py` | Validates the HCC-003 common-grid result. |
| `scripts/` | `validate_hcc003_full_geometry.py` | Validates full HCC-003 geometry. |
| `scripts/` | `validate_hcc104_tmp_seg.py` | Validates temporary HCC-104 segmentation data. |
| `scripts/` | `verify_hcc003_raw_frames.py` | Verifies raw HCC-003 frames. |
| `scripts/` | `verify_hcc003_source_uid_mapping.py` | Verifies HCC-003 source UID mapping. |
| `scripts/` | `verify_hcc048_corrected_coordinates.py` | Verifies corrected HCC-048 coordinates. |
| `scripts/` | `verify_hcc089_pixel_encoding.py` | Verifies HCC-089 pixel encoding. |
| `scripts/` | `verify_hcc089_reference_geometry.py` | Verifies HCC-089 reference geometry. |
| `scripts/` | `visualize_hcc003_segments.py` | Visualizes HCC-003 segmentation results. |
| `scripts/` | `visualize_hcc019_tumor.py` | Visualizes the HCC-019 tumor. |

### `results/`

`results/dataset_audit/` contains generated, reproducible audit artifacts.
Every file below this directory is an output rather than a source input. The
current scan includes 104 CSV files across the project; the six CSV files added
since the previous inventory are covered by the same result-table patterns
below.

| File pattern/location | Type | What it contains |
|---|---|---|
| `results/dataset_audit/*.json` | JSON | Machine-readable audit summaries and structured findings, including `audit_summary.json`. |
| `results/dataset_audit/*.csv` | CSV | Audit tables for inventories, UID linkage, geometry, coverage, reconciliation, candidate series, and review manifests. |
| `results/dataset_audit/*.log` | Log text | Captured output from audit and validation runs. |
| `results/dataset_audit/*.txt` | Plain text | Detailed series metadata or inspection output. |
| `results/dataset_audit/**/*.md` | Markdown | Human-readable review notes, notably the HCC-104/HCC-105 Phase 2 review. |
| `results/dataset_audit/**/*.png` | PNG image | Generated slice, geometry, tumor, mask, and coordinate overlays for visual QC. |

The concrete result files include `audit_summary.json`,
`hcc003_series_metadata.txt`, `ctorg_duplicates.csv`,
`ctorg_label_distribution.csv`, `ctorg_nifti_details.csv`,
`ctorg_pairs.csv`, all HCC inventory/linkage/geometry/audit CSVs, and the
overlay manifests and images in the named HCC-003, HCC-015/016, HCC-048,
HCC-089, and HCC-104/105 subdirectories. Their filenames identify the
specific audit or visualization stage; their contents are tabular findings,
run logs, review templates, summaries, or rendered QC images.

### `.venv/`

`Implementation/ctorg_three_models_starter/.venv/` is a local Python virtual
environment. It contains the interpreter environment,
installed dependencies, package metadata, test fixtures, compiled extension
modules, bytecode, and documentation for packages such as NumPy, pandas,
matplotlib, nibabel, pydicom, Pillow, openpyxl, setuptools, pip, and related
dependencies.

All files below `.venv/` are covered by these exhaustive location/type
patterns:

| Location pattern | Type | Name/content |
|---|---|---|
| `.venv/Scripts/*` | Python environment scripts | Activation/deactivation scripts and executable entry points. |
| `.venv/Lib/site-packages/<package>/**/*.py` | Python source | Installed third-party package implementation modules. |
| `.venv/Lib/site-packages/<package>/**/*.pyi` | Python stubs | Static typing interfaces for installed packages. |
| `.venv/Lib/site-packages/<package>/**/*.pyc` | Python bytecode | Compiled imports generated by Python. |
| `.venv/Lib/site-packages/<package>/*.dist-info/**/*` | Package metadata | Installation metadata, licenses, entry points, dependency records, and top-level package lists. |
| `.venv/Lib/site-packages/**/*.dll` / `*.pyd` | Native binary | Compiled NumPy, pandas, and other native extension libraries. |
| `.venv/Lib/site-packages/**/*.json` / `*.ini` / `*.cfg` / `*.toml` | Configuration/data | Package configuration, test data, schemas, and metadata. |
| `.venv/Lib/site-packages/**/*` with other extensions | Package resources | Fonts, JavaScript/CSS, sample data, scientific fixtures, licenses, and test resources. |
| `.venv/pyvenv.cfg` | Virtual-environment configuration | Python executable/version and environment configuration. |

These are dependency-owned files, not project-authored application logic.
They are included in the inventory because they are physically present under
the local project tree, but they are excluded from version control.

## Inventory completeness

The inventory covers:

1. Every root file by exact name.
2. Every document under `Docs/` by exact name.
3. Every CT-ORG checksum, README, and NIfTI label by exact name/range.
4. Every HCC patient directory (`HCC_001` through `HCC_105`), its DICOM files,
   and the metadata CSV by deterministic path pattern.
5. Every implementation model file and all 82 analysis scripts by exact name.
6. Every result file by exhaustive extension/location pattern.
7. Every virtual-environment file by exhaustive package/resource pattern.

`doc.md` is the generated inventory and is included as a root-level Markdown
file. The file counts above describe the local working-tree scan; they do not
represent the number of files tracked by GitHub because `DATASETS/` and
`.venv/` are excluded.
