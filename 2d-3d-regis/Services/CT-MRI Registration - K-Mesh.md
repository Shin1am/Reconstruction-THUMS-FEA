---
tags: [service, notebook, registration]
---

# CT/MRI Registration — LS-DYNA `.k` Mesh Version

**Location:** `Code/CT_MRI_Registration_K_Mesh.ipynb`
**Type:** Jupyter notebook (SimpleITK only, no ANTs)
**Part of:** [[Architecture#Registration Pipeline (SimpleITK)]]

## Purpose

Same 5-stage pipeline as [[CT-MRI Registration - Clean]], but the **moving** data is read directly from a `.k` LS-DYNA mesh instead of a `.nii.gz` volume — this is the notebook that actually consumes the head-only extraction output for registration.

## Stages (differences from [[CT-MRI Registration - Clean]])

| Cell | Stage | Notes |
|---|---|---|
| 3 | `.k` reader & voxelizer | parses `*NODE`/`*ELEMENT_*`; produces `nodes_original` (N×3 array), `node_id_map` (LS-DYNA node ID → row index), and a voxelized moving image for registration |
| 5–8 | Preprocess / Rigid / Affine / Deformable | identical stage sequence to the Clean version, operating on the voxelized mesh |
| 9 | **Apply transform to `.k` mesh nodes → write new `.k`** | Every node XYZ in `nodes_original` is passed through `FINAL_TX.TransformPoint()` (composed initial→rigid→affine→deformable transform); transformed coordinates replace the originals directly in the raw `.k` lines; written as `<stem>_registered.k` |
| 10 | Validation | alpha blend + checkerboard + Dice |

Key point encoded in the notebook: voxelization is only used to *compute* the transform. The deformed output is always produced by applying the final composite transform straight to the original mesh node coordinates — never by resampling a voxel grid — avoiding staircasing artifacts on thin skull shell elements.

## Inputs

- `.k` mesh file — designed to consume [[extract_head]] / [[extract_head_right]] output (`Head_V6.k`, `Head_V6_head_only.k`, `Head_V6_right_hemi.k`)
- Fixed CT/reference volume (`.nii.gz`)

## Outputs

- `<stem>_registered.k` — warped LS-DYNA mesh, all node coordinates updated, structure otherwise unchanged

## Dependencies

- [[extract_head]] / [[extract_head_right]] — supplies the moving `.k` mesh
- Shares its core registration stage logic with [[CT-MRI Registration - Clean]]

## Used by / feeds into

- [[k_mesh_qa]] — the `<stem>_registered.k` output should be run with `--compare` against the pre-warp baseline before any solver attempt

[[Architecture|← Back to Architecture]]
