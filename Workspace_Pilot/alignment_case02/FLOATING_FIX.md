# Floating posterior nodes: diagnosis and experimental correction

Tracked 62 original exported FE skin nodes in the diagnostic posterior ROI Y>190, Z>-800 mm. This spatial criterion is an outlier diagnostic, not an anatomical label.

Stage replay: posterior outliers already exist after initial TPS (76 nodes in ROI), remain after ICP (57), and reach 62 after the 500-control final TPS. For the same tracked original node IDs, mean CT nearest-vertex distance after initial TPS is 20.89 mm, after ICP 20.12 mm, final TPS 20.18 mm. Increasing final controls to 2000 alone leaves 58 posterior outliers. Thus sparse final TPS is not the primary cause. The 15 mm ICP rejection prevents recovery of many distant posterior points.

Experimental change: ICP acceptance decreases linearly from 40 to 15 mm over 40 iterations. Rejected displacements remain zero after smoothing. Per-iteration displacement is capped at 1 mm. The pre-rigid/PCA confidence fallback is bypassed in this experiment. Final TPS uses 1000 FPS controls and 5000-node batches, one mapping for skin and interior. Changes are combined; no individual causal attribution to all parameters is claimed.

Actual exported FE skin: mean 6.539 -> 4.035 mm; RMS 13.283 -> 11.350 mm; bidirectional HD95 34.996 -> 22.806 mm. Posterior ROI count 62 -> 2. Maximum FE-to-CT error worsens 62.546 -> 67.989 mm. Basal protrusion remains/worsens. Metrics are sampled nearest-vertex distances, not anatomical correspondence.

Heuristic QA suspect count 7287 -> 7507 (baseline 7117); newly flagged relative to baseline 364 -> 632. These are not certified element Jacobian inversion counts. This experiment improves posterior surface fit but is NOT accepted as an FE-safe replacement. Original outputs are preserved.

Files: ../CPD_TPS_case02_floating_fix.ipynb, executed counterpart, ../pilot_case02_floating_fix/, stage_diagnostics.json, floating_before_after.png. Next work: identify original skin boundary faces vs true external skin at the base, verify matched anatomical landmarks, then apply FE-aware constraints before adopting volume deformation.
