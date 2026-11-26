# case_02 alignment inspection

Actual exported FE skin compared with the CT head-and-upper-neck target. No additional registration was applied for these figures. Units: mm; CT coordinates are recorded as LPS by the existing preparation pipeline; source DICOM metadata are unavailable locally for independent confirmation.

- overlay_heatmap.png: front, side, top overlay and FE-to-CT nearest-vertex distances.
- reverse_heatmap.png: CT-to-FE nearest-vertex distances. Sampling densities differ; these are diagnostic point-set distances, not triangle-surface or anatomical correspondence errors.
- regional_metrics.csv: source vertices grouped by the previous crop plane Z >= -912 + 0.28*(Y+20). Nearest neighbors are searched on the whole opposite surface. Head/upper-neck labels are geometric provisional ROIs, not anatomical labels. The same spatial plane is applied independently to exported FE and CT vertices; deformation can change region membership.
- FE_skin_error.vtp / CT_skin_error.vtp: geometry with error scalar arrays.
- alignment_audit.json / executed_output.txt: coordinates and actual registration initialization.

The overlay supports broadly matching superior/inferior and anterior/posterior orientation, but does not verify left/right anatomical identity. Largest discrepancies occur near basal/neck surfaces and posterior protruding points. Outer-part boundary extraction can include cut faces or inner faces; these should be checked before attributing all errors to external skin shape.

No matched landmarks exist for case_02. PCA was used and rigid CPD scale was 1.0. Anatomical seed validation remains incomplete.

## Landmark selection

Run `.venv/bin/python alignment_case02/pick_landmarks.py` from the workspace in a graphical session. Select the SAME anatomical points in identical order in original template (left) and CT (right). Use points that are visible and identifiable on both geometries; right-click picks, close when done. At least four well-spread non-coplanar pairs are recommended. Inspect the saved pending picks and anatomical pairing before copying to project/Data/landmarks_matched. The picker has only been syntax/API checked; interactive picking has not been validated in this run. No points were guessed or enabled automatically.

This inspection does not certify FE validity or internal anatomical accuracy.
