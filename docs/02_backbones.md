# Backbones, read-out bases and components

## The question

The delivered pipeline uses one set of pretrained weights, one feature basis and one set of
component settings. Would another combination do better, and can that be established at
this sample size?

## How it was measured

Eleven sets of pretrained weights, covering two architectures, three self-supervised
recipes and both in-domain and out-of-domain pretraining data. Seven ways of reading
features out of a transformer and three for a convolutional network. A component menu
crossing the power transform, the shrinkage coefficient, the fitting scope and the pooling
rule.

Every cell is evaluated in both cross-center directions with the paired bootstrap. The
strongest candidates were then re-evaluated in a true cross-center setting, where the head
is fitted on all of one center and scored on all of the other.

## The decision rule

Registered before the grid ran, and stated negatively: the output of the grid is a
measurement, not a selection. Report every cell. Do not take the maximum. Adopt only what
is detectably better in both directions.

## Results

The A+ / A− / B± / C / D / E columns classify each cell on **AUROC**. The result files
for these grids record the difference in the ranking metric as a point estimate without an
interval, so the ranking metric cannot be used for detectability here; where a separate
run did provide both, the E3 A+ count under the two-key rule is 36 rather than 39. The
"double-key conflicts" column counts cells where the AUROC difference and the
ranking-metric point estimate disagree in sign. A dash means the conflict count was not
recorded for that family.

| Experiment family | Backbones | Cells | A+ | A− | B± | C | D | E | double-key conflicts | Verdict | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Read-out basis x component (E3) | 11 | 474 (96 dup removed) | 39 | 14 | 28 | 101 | 259 | 33 | 86 | 39 improve in both directions, 14 degrade | `e3_basis_component.json` |
| Layer 3+4 replication (E3b) | 8 | 192 (96 dup removed) | 0 | 7 | 5 | 32 | 148 | 0 | 43 | none improve, 7 degrade | `e3b_cnn_layer.json` |
| Backbone x module interaction | 4 | 48 | 0 | 0 | 9 | 23 | 16 | 0 | - | none improve | `b1_backbone_module.json` |
| Field-of-view mask | 4 | 16 | 0 | 0 | 0 | 14 | 2 | 0 | - | none improve | `c2_fov_mask.json` |
| Fit-scope arm D | 4 | 16 | 0 | 4 | 2 | 0 | 9 | 1 | - | none improve, 4 degrade | `c4_arm_d.json` |
| Instance selection (MIL) | 11 | 33 | 3 | 0 | 0 | 7 | 22 | 1 | - | 3 improve in both directions | `r5_mil.json` |
| Layer choice | 11 | 11 | 1 | 0 | 1 | 0 | 9 | 0 | - | 1 improve in both directions | `r4_layer.json` |
| Same-backbone head fusion | 11 | 99 | 0 | 25 | 31 | 32 | 9 | 2 | - | none improve, 25 degrade | `r6_fusion.json` |
| Multi-backbone fusion | - | 10 | 0 | 0 | 1 | 3 | 6 | 0 | - | none improve | `r7_bbfusion.json` |
| TTA and color normalization | 10 | 30 | 0 | 1 | 0 | 15 | 12 | 2 | - | none improve, 1 degrade | `r8_tta_color.json` |
| External covariance target | - | 27 | 0 | 4 | 9 | 13 | 1 | 0 | - | none improve, 4 degrade | `r2_extcov.json` |
| One-class vs discriminant | 11 | 44 | 0 | 40 | 0 | 0 | 4 | 0 | - | none improve, 40 degrade | `q1_oneclass_all.json` |
| Geometric read-outs | 8 | 32 | 0 | 4 | 4 | 8 | 15 | 1 | 1 | none improve, 4 degrade | `q3_geometry_all.json` |
| Greedy combination search | 11 | 11 | 1 | 3 | 0 | 0 | 2 | 5 | - | 1 improve in both directions, 3 degrade | `r11_combo.json` |
| Normalization family | 11 | 176 | 0 | 33 | 9 | 89 | 43 | 2 | - | none improve, 33 degrade | `d2_norm_family.json` |
| All backbones, A-class components | 11 | 616 | 17 | 51 | 14 | 397 | 124 | 13 | - | 17 improve in both directions, 51 degrade | `d1_all_backbones.json` |

Not included, and why:

* `c1_pooling_ops.json` (Pooling operator x backbone): no delta field

The strongest candidates from those grids were then re-run under true cross-center
evaluation, where the head is fitted on all of one center and scored on all of the other.
That is the setting the delivered pipeline is judged in, and it is the only one in which a
replacement backbone would actually have to win. Thirteen candidates were taken through it:

| Backbone | Read-out | dPPV c2 to c1 | dPPV c1 to c2 | dAUROC c2 to c1 | dAUROC c1 to c2 | verdict on ranking metric | verdict on AUROC |
|---|---|---|---|---|---|---|---|
| DINOv2-ViT-B | B2 | +0.0163 | +0.1640 | +0.0159 | -0.0027 | D | D |
| ViTS-gastro | B3 | +0.0434 | -0.1007 | -0.0023 | +0.0058 | D | D |
| RN50-SWSL | A1 | -0.0517 | +0.0452 | -0.0410 | +0.0045 | D | E |
| RN50-SWSL | A3 | -0.0285 | -0.2550 | -0.0086 | -0.0073 | D | D |
| RN50-1M | A1 | -0.0078 | -0.1688 | +0.0024 | +0.0033 | D | D |
| RN50-200K | A1 | -0.0478 | -0.1688 | -0.0517 | +0.0017 | D | E |
| RN50-MOCOv2 | A1 | -0.0411 | -0.4450 | -0.0596 | -0.0437 | D | A− |
| RN50-MOCOv2 | A3 | -0.0441 | -0.4680 | -0.0408 | -0.0283 | D | A− |
| RN50-SIMCLRv2 | A1 | -0.0508 | -0.4936 | -0.0914 | -0.0762 | A− | A− |
| RN50-in1k-sup | A1 | -0.0660 | -0.5050 | -0.2250 | -0.1942 | A− | A− |
| RN50-in1k-dino | A1 | -0.0604 | -0.4854 | -0.1308 | -0.0704 | A− | A− |
| ViTS-in1k-dino | B1 | -0.0640 | -0.5026 | -0.2218 | -0.1315 | A− | A− |
| ViTS-in1k-dino | B6 | -0.0638 | -0.5034 | -0.1681 | -0.1088 | A− | A− |

A− means detectably worse in both directions; E means the effect reverses with the training center; D means tested but not detected. A+ occurs nowhere in this table.

Across every family, 61 cells improve in both directions. All but
1 are on a ViT, and the exception is on out-of-domain convolutional
weights. On the delivered backbone the count is 0.

The preferred settings point in opposite directions by backbone. Convolutional networks
want the power transform on and all cells used when fitting; the two in-domain transformers
want it off and only the strongest quarter of cells. The same read-out basis is a
detectable improvement on one transformer and a detectable degradation on another, both
pretrained with DINO-family objectives.

## Conclusion

No alternative configuration is detectably better than the delivered one in both
directions. Component effects do not transfer across sets of weights, and the pattern
follows the specific weights rather than the architecture family.

## Limitations

Every result here is conditional on a set of basis choices that were never shown to be
optimal. That limitation applies symmetrically to all eleven backbones, which is why the
comparison is still meaningful, but it means "not detectably better" is a statement about
this configuration space and this sample size, not a general ranking.
