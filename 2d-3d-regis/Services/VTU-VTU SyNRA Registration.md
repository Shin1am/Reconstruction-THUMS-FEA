---
tags: [service, notebook, registration]
---

# VTU↔VTU Registration — ANTsPy SyNRA

**Location:** `Code/VTU_to_VTU_SyNRA_Registration.ipynb` and `Code/VTU_to_VTU_SyNRA_Registration_FIXED.ipynb`
**Type:** Jupyter notebook (ANTsPy)
**Part of:** [[Architecture#VTU↔VTU SyNRA Registration (ANTsPy)]]

## Purpose

An alternative, mesh-to-mesh registration path using ANTsPy's **SyNRA** (Rigid → Affine → diffeomorphic SyN, run as a single composite transform). Both fixed and moving inputs are `.vtu` meshes — no `.nii.gz` round-trip required from the user (meshes are voxelized internally). This is the "SyN" side of the SyN-vs-CPD/TPS registration-method debate: diffeomorphic (no self-intersections) but tuned for dense voxel-intensity matching rather than sparse landmark data — its inversion-count results (via [[k_mesh_qa]]'s metric) are meant to be benchmarked against a future CPD/TPS implementation.

`_FIXED` adds a `recentre_vtu()` helper (raw VTK, not PyVista) that translates a mesh so its centroid aligns with a target center before voxelization — the fix for a unit/origin misalignment issue found in the original version.

## Stages

| Cell | Stage |
|---|---|
| 1 | Install |
| 2 | Config |
| 3 | Load both VTU + voxelize (auto mm/m unit-scale correction, Gaussian blur for smooth SyN gradients, bounding-box margin padding) |
| 4 | ANTsPy SyNRA registration — internally runs Rigid (6-DOF) → Affine (12-DOF) → SyN diffeomorphic warp, output as one composite transform `[warp_field.nii.gz, affine.mat]` |
| 4b | Overlay visualization |
| 5 | Apply SyNRA warp to mesh nodes → new `.vtu`, via `ants.apply_transforms_to_points()`; all point/cell/field data preserved via deep copy; adds `displacement_mm` array |
| 6 | Final validation + output summary |

## Inputs

- `FIXED_VTU` — e.g. `ImageToStl.com_head_voxels_transform.vtu` (head-voxel surface mesh, produced upstream via [[STL to VTK Converter]] and/or an earlier registration pass)
- `MOVING_VTU` — e.g. `Head_V6.vtu`, produced by [[K to VTK Converter]] from the THUMS head extraction

## Outputs

- `Head_V6_synra_registered.vtu` and companion validation PNGs — see [[Architecture#Data Assets]]
- Intermediate voxelized/warped `.nii.gz` volumes (`fixed_voxelized.nii.gz`, `moving_voxelized.nii.gz`, `moving_warped_synra.nii.gz`)

## Dependencies

- [[K to VTK Converter]] — supplies `Head_V6.vtu` as the moving mesh
- [[STL to VTK Converter]] — supplies the head-voxel surface mesh used (after an earlier transform) as the fixed mesh

## Used by / feeds into

- Alternative to [[CT-MRI Registration - VTU-Mesh]] for the deformable warp stage; both operate on the same `.vtu` inputs so results are directly comparable
- [[k_mesh_qa]] does not currently parse `.vtu`, so this notebook's output is validated only by its own built-in Cell 6 checks, not the shared QA gate

[[Architecture|← Back to Architecture]]
