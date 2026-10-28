Ok now could you summarize all the lit review we talked for me, including those
that have similar pipeline with us, what they have done (those that ues CT/MTI
as baseline) and what is the outcome from that research

Head-Model Morphing Literature Summary

Most of the literature we discussed clusters into CT/MRI-driven personalization, template-to-subject morphing,

and the gap between those approaches and your FLAME/MICA shell-only idea. The strongest overall pattern is

that imaging-based pipelines can preserve anatomy and mesh quality well enough for simulation, but they do that

because they start with internal anatomy from CT or MRI (Giudice et al., 2020; Li et al., 2020; Henningsen et al.,

2024).

Imaging-Based Pipelines

These studies are the closest established foundation for subject-specific head FE modeling. They start from

segmented CT or MRI, register a baseline atlas or FE model, then propagate the displacement field into the mesh

(Li et al., 2020; Henningsen et al., 2024; Zapf et al., 2025).

•

•

•

Giudice et al. used nonlinear MRI registration to morph brain FE models for 44 subjects, and strain predictions
differed by less than 4% from manually created voxel models (Giudice et al., 2020).

Li and Kleiven built the ADAPT personalization pipeline from baseline and subject T1 MRI using Demons plus

Dramms, and generated six subject-specific head models with satisfactory element quality and region-level
DICE accuracy (Li et al., 2020).

Henningsen et al. segmented PMCT skull and intracranial layers, morphed ADAPT to five forensic cases, and

preserved subject-specific geometry and mesh quality in all cases (Henningsen et al., 2024).

Pipelines Similar To Yours

The papers most similar to your pipeline are not FLAME/MICA papers, but surface- or template-driven morphing

papers that deform a validated baseline model to a target shape. They show the method is feasible, but also show

why the head is the hardest region (Li et al., 2023; Zhang et al., 2017; Bucki et al., 2010).

Study Type

What They Did

Outcome

THUMS body
morphing

Morphed THUMS and other HBMs
to subject geometries by image

Personalized HBMs had comparable element
quality, but naive THUMS head morphing produced

registration

an unusual head shape (Li et al., 2023)

THUMS avatar-

Used RBF interpolation to adapt

Chest and torso overlap was strong, and anatomical

driven morphing

THUMS v6 across anthropometries

fidelity was broadly preserved with some localized
distortion risk (Reyes et al., 2026)

Face-template FE

Deformed a facial template with

Generated high-quality patient-specific hexahedral

morphing

landmarks, dense fitting, and TPS

meshes with good internal structure
correspondence (Zhang et al., 2017)

1 / 3

Study Type

What They Did

Outcome

Atlas mesh
registration

Registered a generic FE mesh to
patient skin and bone surfaces

Succeeded in 60 cases with submillimetric surface
accuracy, including 50 head CT cases (Bucki et al.,

2010)

FIGURE 1  Pipelines most similar to shell-driven THUMS personalization

What CT/MRI Baselines Achieve

Across the CT/MRI-based papers, the main benefit is not just fitting the outside surface. The imaging provides

internal boundaries, ventricles, CSF spaces, white matter tracts, and tissue layers, which lets the morphed

model stay anatomically meaningful inside (Li et al., 2020; Huynh et al., 2025; Bahreinizad et al., 2024).

•

•

•

Lifespan and pathology pipelines handled newborn, elderly, and hydrocephalus brains by adding feature-

based and multimodality registration steps (Li, 2021).

SynthMorph-based atlas morphing produced 300+ labeled structures in about 20 minutes while maintaining

high Dice, low Hausdorff distance, and high mesh quality (Huynh et al., 2025).

Earlier atlas-space meshing achieved 0.07 mm average surface error and 99.5% of elements with scaled

Jacobian above 0.6, showing that registration-based meshing can be both accurate and fast (Ji et al., 2011).

Main Outcome For Your Project

The literature supports morphing a validated baseline mesh to a subject shape, but it does not yet show a paper

that morphs THUMS head directly to a FLAME/MICA outer shell and then recovers a truly individualized internal

head anatomy. The closest THUMS paper actually found that direct head morphing could fail because of topology
differences, and solved that case by shielding the head rather than personalizing it (Li et al., 2023).

What the broader literature does support is a publishable surface-constrained personalization strategy: use the

shell to drive outer-shape morphing, propagate the field inward smoothly, and treat the inside as atlas-inherited
anatomy unless additional CT/MRI or statistical priors are added (Li, 2021; Zapf et al., 2025). That framing is also

consistent with adjacent modeling work showing that realistic anatomy improves predictions, while surface

conversion or coarse representations can lose important interface detail (Huang et al., 2017; Zhou et al., 2025;
Tizzard et al., 2005).

So the short summary is: CT/MRI-based pipelines are proven, template morphing is proven, but THUMS-to-

FLAME shell-only individualized head modeling still looks like an open research problem rather than an
established method.

These search results were found and analyzed using Consensus, an AI-powered search engine for research. Try it at

https://consensus.app. © 2026 Consensus NLP, Inc. Personal, non-commercial use only; redistribution requires
copyright holders’ consent.

References

Bahreinizad, H., Chowdhury, S., Paulon, G. M., Wei, L. H., & Santos, F. Z. (2024). Development and Validation of an
MRI-Derived Head-Neck Finite Element Model. bioRxiv. https://doi.org/10.1101/2023.02.12.528203

Bucki, M., Lobos, C., & Payan, Y. (2010). A fast and robust patient specific Finite Element mesh registration

technique: Application to 60 clinical cases. Medical image analysis, 14 3, 303-17.
https://doi.org/10.1016/j.media.2010.02.003

2 / 3

Giudice, J. S., Alshareef, A., Wu, T., Gancayco, C. A., Reynier, K., Tustison, N., Druzgal, T. J., & Panzer, M. (2020). An

Image Registration-Based Morphing Technique for Generating Subject-Specific Brain Finite Element Models.

Annals of Biomedical Engineering, 48, 2412 - 2424. https://doi.org/10.1007/s10439-020-02584-z

Henningsen, M. J., Lindgren, N., Kleiven, S., Li, X., Jacobsen, C., & Villa, C. (2024). Subject-specific finite element

head models for skull fracture evaluation—a new tool in forensic pathology. International Journal of Legal

Medicine, 138, 1447 - 1458. https://doi.org/10.1007/s00414-024-03186-3

Huang, Y., Datta, A., Bikson, M., & Parra, L. (2017). Realistic volumetric-approach to simulate transcranial electric

stimulation—ROAST—a fully automated open-source pipeline. Journal of neural engineering, 16, 056006 -

056006. https://doi.org/10.1088/1741-2552/ab208d

Huynh, A., Zwick, B., Halle, M., Wittek, A., & Miller, K. (2025). Personalizing the meshed SPL/NAC Brain Atlas for

patient-specific scientific computing using SynthMorph. ArXiv, abs/2503.00931.

https://doi.org/10.48550/arxiv.2503.00931

Ji, S., Ford, J. C., Greenwald, R., Beckwith, J., Paulsen, K., Flashman, L., & McAllister, T. (2011). Automated subject-

specific, hexahedral mesh generation via image registration. Finite elements in analysis and design : the

international journal of applied finite elements and computer aided engineering, 47, 1178 - 1185.
https://doi.org/10.1016/j.finel.2011.05.007

Li, X., Zhou, Z., & Kleiven, S. (2020). An anatomically detailed and personalizable head injury model: Significance of

brain and white matter tract morphological variability on strain. Biomechanics and Modeling in Mechanobiology,
20, 403 - 431. https://doi.org/10.1007/s10237-020-01391-8

Li, X., Yuan, Q., Lindgren, N., Huang, Q., Fahlstedt, M., Östh, J., Pipkorn, B., Jakobsson, L., & Kleiven, S. (2023).
Personalization of human body models and beyond via image registration. Frontiers in Bioengineering and

Biotechnology, 11. https://doi.org/10.3389/fbioe.2023.1169365

Li, X. (2021). Subject-Specific Head Model Generation by Mesh Morphing: A Personalization Framework and Its
Applications. Frontiers in Bioengineering and Biotechnology, 9. https://doi.org/10.3389/fbioe.2021.706566

Li, X. (2021). Head model personalization: A framework for morphing lifespan brain images and brains with

substantial anatomical changes. bioRxiv. https://doi.org/10.1101/2021.04.10.439281

Reyes, A. N., DeWitt, T. R., & Kraft, R. H. (2026). Personalization of the Toyota Human Model for Safety (THUMS)

Using Avatar-Driven Morphing for Biomechanical Simulations. Biomechanics.

https://doi.org/10.3390/biomechanics6020037

Tizzard, A., Horesh, L., Yerworth, R., Holder, D., & Bayford, R. (2005). Generating accurate finite element meshes

for the forward model of the human head in EIT. Physiological Measurement, 26, S251 - S261.

https://doi.org/10.1088/0967-3334/26/2/024

Zapf, B., Haubner, J., Baumgärtner, L., & Schmidt, S. (2025). Medical Image Registration using optimal control of a

linear hyperbolic transport equation with a DG discretization. ArXiv, abs/2305.03020.
https://doi.org/10.48550/arxiv.2305.03020

Zhang, X., Kim, D., Shen, S., Yuan, P., Liu, S., Tang, Z., Zhang, G., Zhou, X., Gateno, J., Liebschner, M., & Xia, J.

(2017). An eFTD-VP framework for efficiently generating patient-specific anatomically detailed facial soft tissue FE
mesh for craniomaxillofacial surgery simulation. Biomechanics and modeling in mechanobiology, 17, 387 - 402.

https://doi.org/10.1007/s10237-017-0967-6

Zhou, Z., Li, X., & Kleiven, S. (2025). Surface-based versus voxel-based finite element head models: comparative

analyses of strain responses. Biomechanics and Modeling in Mechanobiology, 24, 845 - 864.

https://doi.org/10.1007/s10237-025-01940-z

3 / 3


