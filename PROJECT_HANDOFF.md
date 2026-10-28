# PROJECT HANDOFF — 2D→3D Head Impact Brain Deformation Pipeline
# Paste this entire document at the start of a new chat to restore full context.

---

## PROJECT IDENTITY

You are an expert AI research collaborator in biomedical engineering,
computational biomechanics, and medical image processing. You are assisting
an undergraduate research team building a "front-end geometry engine" for
head-impact brain deformation simulations.

**Goal**: Take non-invasive data (2D sports/boxing video footage) and
reconstruct personalized 3D anatomical structures ready for downstream
Finite Element Analysis (FEA) to assess concussion risk.

---

## CORE RESEARCH PIPELINE

1. **2D → 3D**: Extract 3D impact kinematics/vectors from 2D video frames at
   moment of impact
2. **3D → Head Shape**: Reconstruct dense personalized external 3D head mesh
   from sparse spatial markers
3. **Head Shape → Skull & Brain Transform**: Take a unified reference template
   (skull + brain aligned together), compute a SINGLE transformation/warp field
   from external head shape, apply to entire multi-component model at once —
   skull and brain deform together, maintaining anatomical alignment
4. **FEA Ready**: Output clean transformed skull+brain geometry for
   biomechanical simulation (target: TSUBAME4.0)

---

## TECHNICAL STACK

- Language: Python 3
- Libraries: NumPy, PyTorch, MONAI, ASTRA Toolbox
- Registration under evaluation: CPD, TPS, ICP (mesh-based) vs ANTsPy/SyN,
  VoxelMorph (voxel-based)
- Reference template: THUMS AM50 V4.1 Pedestrian full-body model (.k files)
- Solver target: LS-DYNA (via TSUBAME4.0 HPC)

---

## CURRENT STATUS (end of last session)

### What we accomplished
1. Confirmed THUMS AM50 V4.1 Pedestrian file structure:
   - Master file: `main_THUMS_AM50_V41.k` (includes only, no mesh data)
   - Mesh data: `THUMS_model/THUMS_AM50_V41_Pedestrian_202506.k`
   - Material data: `THUMS_model/mat_bone_AM50_V41_Ped_no_fracture.k`
   - Element format: **fixed-width I8 (8-char, no delimiter)** — non-standard
   - Full model: 772,156 nodes, 1,527,480 solid elements, 443,144 shell elements
   - 501 total parts

2. Built and iteratively debugged 3 Python scripts (see below)

3. Identified all head-region PIDs — skull uses **bone names** not "skull":
   - Cranial vault: frontal/parietal/temporal/occipital/sphenoid/ethmoid
     PIDs 88000001–88000020 (R) and 88000052–88000070 (L)
   - Full facial skeleton: PIDs 88000001–88000099 (R+L)
   - Brain: 88000100–88000125 (white/gray matter, cerebellum, brainstem R+L)
   - Meninges+CSF: 88000106–88000142, 88000242–88000255 (dura, pia, arachnoid,
     CSF layers, falx, tentorium, ventricles)
   - Head skin: 88000167–88000172, 88000219–88000236
   - Eyes: 88000173–88000216
   - Face muscles/jaw: 88000143–88000166

4. Ran `extract_head.py --minimal` (skull+brain+meninges):
   - **Result: 167,986 nodes — OVER the 128K LS-DYNA Student cap**
   - Root cause: MINIMAL_PIDS included full facial skeleton (88000001–88000099)
     which adds lacrimal/nasal/zygomatic/maxilla/mandible/palatine/teeth —
     none of which are relevant to intracranial skull-brain deformation

### IMMEDIATE NEXT TASK (pick up here)

**Fix the node count by switching to cranial-vault-only skull extraction.**

Replace `MINIMAL_PIDS` in `extract_head.py` with:

```python
SKULL_CRANIAL_VAULT_R = [
    88000001, 88000002, 88000003,   # frontal R
    88000004, 88000005, 88000006,   # parietal R
    88000007, 88000008, 88000009, 88000010,  # temporal R
    88000011, 88000012, 88000013,   # occipital R
    88000014, 88000015, 88000016,   # sphenoid R
    88000017, 88000018, 88000019, 88000020,  # ethmoid R
]
SKULL_CRANIAL_VAULT_L = [
    88000052, 88000053, 88000054,   # frontal L
    88000055, 88000056, 88000057,   # parietal L
    88000058, 88000059, 88000060, 88000061,  # temporal L
    88000062, 88000063, 88000064,   # occipital L
    88000065, 88000066, 88000067,   # sphenoid L
    88000068, 88000069, 88000070,   # ethmoid L
]
SKULL_CRANIAL_VAULT = SKULL_CRANIAL_VAULT_R + SKULL_CRANIAL_VAULT_L

MINIMAL_PIDS = set(SKULL_CRANIAL_VAULT + BRAIN + MENINGES_CSF)
```

Then re-run:
```powershell
python extract_head.py "C:\Mai\BME\BioDat Work\2D-3D-Mri-image\New_version\AM50 V4.1 Pedestrian\main_THUMS_AM50_V41.k" --minimal
python k_mesh_qa.py "...\_head_minimal.k"
```

Expected result: ~80–110K nodes (under 128K cap).

---

## FILE PATHS ON USER'S MACHINE

```
Base dir : C:\Mai\BME\BioDat Work\2D-3D-Mri-image\New_version\AM50 V4.1 Pedestrian\
Master k : main_THUMS_AM50_V41.k
Mesh k   : THUMS_model\THUMS_AM50_V41_Pedestrian_202506.k
Mat k    : THUMS_model\mat_bone_AM50_V41_Ped_no_fracture.k
Alt path : D:\2d_3d_regis dataset\AM50 V4.1 Pedestrian\ (same files, different drive)
```

---

## TOOLS & LICENSES

- **ANSYS Student** (installed): Workbench-based, NO LS-DYNA solver included
- **ANSYS LS-DYNA Student** (downloading): separate product, includes LS-DYNA
  solver, capped at **128K nodes/elements** — this is the solve target
- **LS-PrePost 2025 R1 v4.12.6** (installed, working): free standalone viewer/
  editor, confirmed opens THUMS file correctly
- No TSUBAME4.0 access confirmed yet (user needs to ask advisor)
- No full research ANSYS license available

### ANSYS Workbench issues encountered (for reference)
- Geometry cell rejects .k files (wrong cell — needs Model cell)
- External Model → LS-DYNA Model link fails with:
  `IABrTopoCell from TopoId=216313 not found` (ACMO topology converter
  chokes on full-body THUMS mixed element types)
- Workaround: use command-line lsdyna.exe directly + LS-PrePost for pre/post

---

## PYTHON SCRIPTS BUILT THIS SESSION

### 1. `k_mesh_qa.py` — Pre-solve mesh quality gate
- Parses .k files following *INCLUDE chains recursively
- Handles fixed-width I8 format (THUMS's element card format)
- Detects inverted/degenerate solid elements (per-PID sign consistency check)
- Detects zero-area shell elements
- Detects coincident nodes
- Use: `python k_mesh_qa.py baseline.k`
- Use: `python k_mesh_qa.py warped.k --compare baseline.k`
- Key design: per-PID majority-sign check (not whole-mesh) to avoid false
  positives from different parts using different node-winding conventions
- Known baseline result: 7,729 flagged solid elements in full-body THUMS
  (0.5% — acceptable for published reference model, likely winding artifacts
  in 56/501 parts with mixed internal winding)

### 2. `list_parts.py` — PID/name extractor
- Dumps all *PART entries with PID + name following includes
- Supports keyword filtering: `python list_parts.py main.k skull brain dura`
- Reads HyperMesh $HMNAME comment annotations for part names
- Use: `python list_parts.py main.k > all_parts.txt`

### 3. `extract_head.py` — Head-only keyword extractor
- Full-fidelity parser: reads nodes, all element types, parts, sections,
  materials, EOS, hourglass cards
- Filters to target PIDs, collects referenced MAT/SEC/EOS/HG cards
  automatically
- Writes self-contained head_only.k (no external includes needed)
- Modes: `--minimal` (skull+brain+meninges), default (full head + skin)
- Current issue: MINIMAL_PIDS uses full facial skeleton → 167K nodes over cap
- Fix: switch to SKULL_CRANIAL_VAULT only (see NEXT TASK above)

---

## KEY TECHNICAL DECISIONS & RATIONALE

### Registration method (not yet finalized)
- **SyN/ANTsPy** argued for by user (diffeomorphic = no self-intersections)
- **Counter-argument**: SyN is optimized for dense voxel-intensity matching
  (CT/MRI gray-white contrast). Our input is sparse 3D landmarks from 2D video,
  not a dense intensity volume. SyN's main strength is unused here.
- **CPD/TPS recommendation**: mesh-native, no voxel round-trip, properly
  regularized TPS is also diffeomorphic in smooth-deformation regime,
  published personalized head-FEA literature (SIMon, ADAPT) uses RBF/TPS
  for landmark-sparse → dense-mesh scenarios
- **Recommended approach**: empirically compare both on k_mesh_qa.py
  inversion-count metric — clean ablation study for paper

### Unified transformation logic
- Single warp field computed from external head shape
- Applied simultaneously to ALL mesh nodes regardless of part (skull or brain)
- Maintains skull-brain alignment by construction
- Shell elements (skull cortical bone) need area/normal-flip checks post-warp
- Solid elements (brain tissue) need Jacobian/volume checks post-warp
- k_mesh_qa.py handles both checks separately

### nii.gz / voxel domain
- Only needed if going SyN/VoxelMorph route
- Key rule: mesh→voxel only for COMPUTING the transform, never for the
  deformed output — always apply displacement field to original mesh node
  coordinates directly to avoid staircasing artifacts on thin skull elements
- If staying CPD/TPS: no nii.gz involved at all

---

## PIPELINE STAGE STATUS

| Stage | Status |
|---|---|
| 2D → 3D kinematics | Not started (future work) |
| 3D → Head shape reconstruction | Not started (future work) |
| Template selection (THUMS AM50 V4.1) | ✅ Confirmed, files located |
| Head-only extraction | 🔄 In progress — node count fix needed |
| Mesh QA tooling | ✅ Complete (k_mesh_qa.py) |
| Baseline solve test | ⏳ Blocked on node count fix + LS-DYNA Student install |
| Registration algorithm (TPS/CPD/SyN) | ⏳ Not started |
| Warp application to mesh | ⏳ Not started |
| Post-warp QA | ⏳ Not started (k_mesh_qa.py --compare ready) |
| FEA solve on TSUBAME | ⏳ Blocked on advisor/access |

---

## OPERATIONAL GUIDELINES FOR CLAUDE

- Technical level: advanced, research-grade, mathematically rigorous
- Unified transformation logic: prioritize methods handling multi-component
  data (multi-channel voxel volumes OR displacement field across multiple
  mesh vertex sets simultaneously)
- Academic focus: precision and terminology appropriate for biomedical
  engineering / computer vision conference papers
- Collaborative tone: peer co-developer, no introductory filler, dive
  directly into technical analysis
- When writing code: clean, optimized Python 3, NumPy/PyTorch/MONAI stack
