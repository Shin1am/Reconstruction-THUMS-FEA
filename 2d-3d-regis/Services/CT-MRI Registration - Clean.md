---
tags: [service, notebook, registration]
---

# CT/MRI Registration — Clean Version

**Location:** `Code/CT_MRI_Registration_Clean.ipynb` and `Code/CT_MRI_Registration_Clean_1.ipynb`
**Type:** Jupyter notebook (SimpleITK only, no ANTs)
**Part of:** [[Architecture#Registration Pipeline (SimpleITK)]]

## Purpose

The reference implementation of the project's 5-stage registration pipeline, operating directly on volumetric images (`.nii.gz`). [[CT-MRI Registration - K-Mesh]] and [[CT-MRI Registration - VTU-Mesh]] both specialize this same stage sequence for mesh I/O instead of image I/O.

`_1` is a near-duplicate iteration of the same notebook (different example file paths, one docstring fix, one cell-order swap in the deformable stage) — functionally the same pipeline.

## Stages

| Cell | Stage | Notes |
|---|---|---|
| 1 | Install dependencies | once per session |
| 2 | User config | set `CT_PATH` (fixed), `MRI_PATH` (moving), `OUTPUT_DIR` |
| 3 | SynthSeg brain prediction (optional) | skull-stripping; `RUN_SYNTHSEG = False` to skip |
| 4 | Imports & helper functions | shared by all downstream cells |
| 5 | Preprocess | load → resample → normalize → center-align |
| 6 | Rigid registration | 6-DOF (rotation + translation), initialized from center-align |
| 7 | Affine refinement | 12-DOF (+ scale + shear), initialized from rigid result |
| 8 | Deformable registration | SimpleITK Demons non-linear warp; `RUN_DEFORMABLE = False` to use affine as final |
| 9 | Validation | alpha blend + checkerboard views, optional Dice score |

## Inputs

- Fixed image: `head-Model-label.nii.gz` (CT / THUMS voxel mask) — [[Architecture#Data Assets|Data assets]]
- Moving image: MRI/segmentation `.nii.gz` volume

## Outputs

- `outputs/case01/` — preprocessed/resampled/rigid/affine/deformable `.nii.gz` volumes + stage validation PNGs

## Dependencies

- Raw `.nii.gz` volumes in [[Architecture#Data Assets|Data/]] — no dependency on the extraction toolkit or format converters, since it works on images, not meshes

## Used by / feeds into

- Conceptual ancestor of [[CT-MRI Registration - K-Mesh]] and [[CT-MRI Registration - VTU-Mesh]] — both reuse this notebook's Preprocess → Rigid → Affine → Deformable → Validation stage sequence, adding a mesh read/write step around it

[[Architecture|← Back to Architecture]]
