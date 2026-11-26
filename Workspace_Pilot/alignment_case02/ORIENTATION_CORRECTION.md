# Correction: orientation and posterior coverage

The earlier statement that anterior/posterior orientation broadly agreed was incorrect. Part-specific inspection shows template face_skin_out parts lie anterior (+template X) and inferior (+template Z is superior). The blind PCA rotation sent face skin toward posterior CT (+Y) and superior, causing face openings and the coarse facial mesh to appear at the occiput. Good surface-only residuals did not establish anatomical orientation.

Case-specific proper seed R=[[0,1,0],[-1,0,0],[0,0,1]] maps template anterior +X to CT anterior -Y, superior +Z to +Z, and lateral template +Y to CT +X. det(R)=+1. This is a geometry/part-informed initialization, not a manually verified paired landmark registration. CT orientation is taken from the existing LPS preparation and visible anterior nose profile, not independently re-read DICOM metadata. This seed is specific to case_02 and this template.

Retained bidirectional surface correspondence and FE-edge displacement smoothing, 100 iterations, gate 45->20 mm, max 0.75 mm step; final TPS 1000 FPS controls, 5000-node evaluation batches; one field for every node, original connectivity unchanged. No surface densification or artificial filling was performed.

Actual exported skin metrics: FE->CT nearest-vertex mean 1.003 mm, RMS 1.187 mm; bidirectional HD95 6.654 mm. Posterior diagnostic ROI CT Y>130: CT->FE mean 1.942 mm, 95th percentile 4.078 mm, 96.86% vertices within 5 mm (previous floating-fix output: 9.947 mm, 36.198 mm, 53.00%). Sampling densities differ and point distances are not true point-to-triangle distances or anatomical correspondence validation.

Heuristic mesh QA: baseline 7117 suspect, final 7109, new IDs relative baseline 261, cleared 273. Count reduction does not establish positive Jacobians or FE safety. Internal anatomy remains unvalidated.

Preferred surface-registration diagnostic notebook: ../CPD_TPS_case02_oriented.ipynb and executed counterpart. Output: ../project/Data/outputs/cpd_tps_case02_oriented/Head_V6_skin_registered_fixed.vtu. Earlier outputs are preserved for comparison but should not be used for anatomical validation because of the incorrect orientation.
