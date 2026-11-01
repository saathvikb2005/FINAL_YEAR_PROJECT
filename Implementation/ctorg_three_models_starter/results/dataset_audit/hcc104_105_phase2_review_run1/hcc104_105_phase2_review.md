# Phase 2 Review ? HCC_104 and HCC_105

## Purpose
Document follow-up checks after the original consolidated audit marked both patients
`NO_FILES_IN_FOLDER`, despite the files being present.

## Findings

### HCC_104
- SEG frames: 396
- Tumor-positive frames: 13
- Tumor-mask pixels: 15312
- CT references: 198/198 referenced CT SOP UIDs found locally
- Geometry: PASS: 396/396 frames
- Visual review: Preliminary visual screening found no obvious alignment failure in reviewed examples
- Slice continuity: 13 unique Z positions; adjacent positive-slice gaps all 2.5 mm
- Recommended status: `PRELIMINARY_QC_PASSED_ANNOTATION_REVIEW_LIMITED`


### HCC_105
- SEG frames: 324
- Tumor-positive frames: 22
- Tumor-mask pixels: 65817
- CT references: 162/162 referenced CT SOP UIDs found locally
- Geometry: PASS: 324/324 frames
- Visual review: Preliminary visual screening found no obvious alignment failure in reviewed examples
- Slice continuity: 22 unique Z positions; adjacent positive-slice gaps all 2.5 mm
- Recommended status: `PRELIMINARY_QC_PASSED_ANNOTATION_REVIEW_LIMITED`

## Limitations and decision
- This report records technical validation and preliminary visual screening, not clinical
  confirmation of annotation correctness.
- The original consolidated audit remains unchanged.
- The original DICOM files and segmentation masks remain unchanged.
- Neither patient is approved for the primary cohort solely by this report.
- Final cohort inclusion requires completion of the project-wide cohort policy and
  resolution of the inconsistent original audit status.
