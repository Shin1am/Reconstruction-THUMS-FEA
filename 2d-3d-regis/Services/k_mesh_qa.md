---
tags: [service, script, python]
---

# k_mesh_qa.py — Pre-Solve Mesh Quality Gate

**Location:** `Code/k_mesh_qa.py` (360 lines)
**Type:** standalone Python script
**Part of:** [[Architecture#Mesh Quality Assurance — k_mesh_qa.py]]

## Purpose

Catches the failure modes that a surface-driven warp (or a hand-curated extraction) commonly introduces into volumetric skull/brain elements, **before** the file ever reaches the LS-DYNA solver.

## Checks performed

1. **Negative/zero Jacobian** (inverted tets/hexes) → guaranteed solver crash
2. **Extreme aspect ratio** → timestep collapse even without a crash
3. **Duplicate/coincident nodes** introduced by a warp field
4. **Zero-area shell elements**
5. **Per-PID majority-sign winding check** — deliberately per-part rather than whole-mesh, to avoid false positives from parts that legitimately use different node-winding conventions

## Usage

```
python k_mesh_qa.py baseline_head.k
python k_mesh_qa.py warped_head.k --compare baseline_head.k
```

## Inputs

- Any `.k` file — pre-warp baseline or post-warp result
- Optional `--compare` baseline file for diffing before/after a registration step

## Outputs

- Console QA report (flagged element IDs, counts, comparison deltas)

## Dependencies

- Runs on output from [[extract_head]], [[extract_head_right]], or [[CT-MRI Registration - K-Mesh]] (all of which produce `.k` files)

## Used by / feeds into

Sits at **two points** in the pipeline:
- **Pre-registration gate**: validates [[extract_head]] / [[extract_head_right]] output before it's handed to a registration notebook
- **Post-registration gate**: (`--compare` mode) validates [[CT-MRI Registration - K-Mesh]] output against its pre-warp baseline

Note: this tool is `.k`-native. [[CT-MRI Registration - VTU-Mesh]] and [[VTU-VTU SyNRA Registration]] write `.vtu` output, which this script does not currently parse — post-warp QA for those two notebooks is not yet wired up.

## Known baseline result

7,729 flagged solid elements (0.5%) in the full-body THUMS reference — accepted as expected winding-convention noise across 56 of 501 parts, not a defect.

[[Architecture|← Back to Architecture]]
