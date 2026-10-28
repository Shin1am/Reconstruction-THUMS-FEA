---
tags: [service, notebook, converter]
---

# LS-DYNA `.k` → VTK Full Converter

**Location:** `Code/K_to_VTK_Converter.ipynb`
**Type:** Jupyter notebook (PyVista)
**Part of:** [[Architecture#Format Converters]]

## Purpose

Full-fidelity conversion of an LS-DYNA `.k` keyword file into a VTK `UnstructuredGrid` — nodes, every element type, parts, materials, and sets. This is the bridge that lets the mesh-based registration and SyNRA notebooks operate on THUMS-derived geometry without a native `.k` parser of their own.

## Stages

| Cell | Stage | Description |
|---|---|---|
| 1 | Install | dependencies |
| 2 | Config | input/output paths |
| 3 | Parser | full `.k` keyword parser — `*NODE`, `*ELEMENT_SOLID` (hex8/tet4/penta6), `*ELEMENT_SHELL` (quad4/tria3), `*ELEMENT_BEAM`/`*ELEMENT_TRUSS`, `*PART`, `*MAT_*`, `*SECTION_*`, `*SET_NODE`/`*SET_NODE_LIST`, `*SET_ELEMENT`, `*BOUNDARY_SPC_NODE` |
| 4 | Builder | assembles a `pyvista.UnstructuredGrid` — point data: `node_id`, per-node-set booleans, `has_spc`; cell data: `element_id`, `part_id`, `material_id`, `section_id`, `element_type`, per-element-set booleans |
| 5 | Writer | saves `.vtk`/`.vtu` + export summary |
| 6 | Validate | load-back check + quick stats |

## What is preserved vs. lost

Fully preserved: node coordinates (float64), node IDs, all element types (hex/tet/penta/shell/beam/truss), part ID and material ID per element, node/element sets. Stored only as VTK field-data metadata (not usable by VTK tooling directly): `*MAT` cards, `*SECTION` cards, boundary conditions. **Not representable at all:** LS-DYNA solver logic.

## Inputs

- `.k` file — typically [[extract_head]] output (`Head_V6.k`)

## Outputs

- `Head_V6.vtu` + `Head_V6_metadata.json` + `part_distribution.png` in `Data/outputs/vtk_export/`

## Dependencies

- [[extract_head]] — supplies the `.k` file this notebook converts

## Used by / feeds into

- [[CT-MRI Registration - VTU-Mesh]] and [[VTU-VTU SyNRA Registration]] — both consume `Head_V6.vtu` as the moving mesh

## Caveat

Because material/section/boundary data survive only as inert metadata, a `.vtu` produced here **cannot** be converted back into a solver-ready `.k` file without re-attaching that data manually — this converter is a one-way bridge for registration/visualization, not a round-trip format.

[[Architecture|← Back to Architecture]]
