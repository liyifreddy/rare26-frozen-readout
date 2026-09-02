# Result files

Each file here backs a specific claim in `docs/` or in the method report. Files that no
conclusion rests on are not included; the working directory holds many more.

## What these files are, and are not

They are aggregated statistics: per-configuration differences, intervals, counts and
timings. There is no image, no crop and no per-image identifier anywhere in them, and
nothing in them can be turned back into the challenge data. One file is the exception to
"aggregated": `t7_train_serve.json` carries sixteen model scores for sixteen unnamed
training frames, because the rank correlation it reports is computed from them and a
reader should be able to recompute it. Sixteen unlabelled scalars identify nothing. The
images themselves belong to the challenge organizers and are distributed by them under
their own terms, not here.

## The main experiment grids

| File | What it supports |
|---|---|
| `e3_basis_component.json` | Read-out basis by component, the largest single grid and the source of the transfer claim. |
| `e3b_cnn_layer.json` | The same grid repeated on a different layer. |
| `d1_all_backbones.json` | All eleven backbones crossed with the A-class components. |
| `d2_norm_family.json` | The normalization family. |
| `b1_backbone_module.json` | Backbone by module interaction. |
| `c1_pooling_ops.json` | Pooling operator by backbone. Carries no difference field, which is why it is absent from the verdict table. |
| `c2_fov_mask.json` | The field-of-view mask. |
| `c4_arm_d.json` | Fit-scope arm D. |
| `q1_oneclass_all.json` | Modeling the normal class alone against fitting a discriminant. |
| `q3_geometry_all.json` | Geometric read-outs. |
| `r2_extcov.json` | An external covariance target. |
| `r4_layer.json` | The choice of layer. |
| `r5_mil.json` | Instance selection. |
| `r6_fusion.json` | Head fusion within one backbone. |
| `r7_bbfusion.json` | Fusion across backbones. |
| `r8_tta_color.json` | Test-time augmentation and color normalization. |
| `r11_combo.json` | Greedy combination search. |
| `p37_summary.json` | Cross-family totals used in the text, produced by the same script that builds the verdict table. |

## The delivered read-out, and the checks on it

| File | What it supports |
|---|---|
| `p23_cross_confirm.json` | Per-position scoring against global average pooling, true cross-center, both directions. |
| `r9_evc_loc.json` | External localization check against five expert delineations, and the expert-agreement measurement. |
| `p22_scale_and_joint.json` | The two-direction joint null control, measured rather than obtained by multiplying single-direction rates. |
| `e5_neutral.json` | Sequential assembly from two different starting points. |
| `r15_paired.json` | The nested search: what selecting on a noisy estimate costs. |

## Candidate backbones under true cross-center evaluation

| File | What it supports |
|---|---|
| `p24_swsl_cross.json` | Two candidate backbones. |
| `p25_cross_all.json` | Nine further candidates, same protocol. |
| `e7_cross.json` | The two transformer candidates that came closest. |

## Fitting and preprocessing

| File | What it supports |
|---|---|
| `lambda_paired.json` | Selection of the shrinkage coefficient, paired across folds. |
| `lambda_endpoint.json` | The same selection read at the endpoints. |
| `audit_2stage.json` | The two-stage resize, 512 then 224, against a single downscale. |
| `t7_train_serve.json` | Training and serving preprocessing compared frame by frame. |
| `t7_skew_cost.json` | What the train-and-serve difference costs when it is not corrected. |

## Deployment and the held-out data

| File | What it supports |
|---|---|
| `p28_384.json` | Container timing and memory on a full-size case. |
| `p29_platform.json` | Platform output against local output, score by score. |
| `p31_platform_leaderboard.json` | The challenge validation results, read from the leaderboard. |
| `p16_labelflip.json` | Label noise: what it costs each of the two keys. |
| `p32_domain_shift.json` | Simulated color and illumination shift, and the three candidate corrections. |
| `p33_structure.json` | Simulated sharpening and compression, and the feature displacement measurement. |
| `p34_ppv_attribution.json` | The same attribution read on the ranking metric. |
| `p35_four_cells.json` | The four-cell verdict on the candidate corrections. |
| `p36_tta_under_shift.json` | What test-time augmentation recovers under shift. |
| `number_table.json` | Every number quoted in the report and in these documents, each with the source it came from. |
| `number_table_en.json` | The English name of every key in `number_table.json`. A mapping only; the authoritative file is the one above. |
| `_untraceable_sources.txt` | The keys whose source is not a file in this repository, listed by name with where each came from instead. |

## How the verdict columns were computed

The A+ / A− / B± / C / D / E columns in `docs/02_backbones.md` and in the report are
produced from these files by one classifier, on the AUROC difference, with a detection
threshold of 0.0165. That classifier is published as `src/verdict.py`; running
`python src/verdict.py --demo` reproduces the `d1_all_backbones` row and exits non-zero if
it does not. The rule it applies:

* **A+** both directions detectable, both positive, and **both** at or above 0.0165
* **A−** the same with both negative
* **B+ / B−** both directions detectable and agreeing in sign, at least one below 0.0165
* **E** the two directions disagree in sign and at least one is detectable at or above 0.0165
* **C** both intervals lie wholly inside the threshold band
* **D** everything else

Detectable means the paired bootstrap interval excludes zero. Three details a reader will
otherwise trip over:

* The difference field is named `d` in most files, `d_tukey` in `b1_backbone_module.json`,
  and `d_minus_c` in `c4_arm_d.json`. In that last file the key `d` is arm D's AUROC, not
  a difference.
* `d1_all_backbones.json` holds 660 two-direction configurations, of which the 44 in the
  `m2|` family carry no difference field. The table's 616 is the remainder. This is the
  same reason `c1_pooling_ops.json` has no row at all.
* The E3 grid holds 570 configurations. On the eight convolutional backbones the feature
  map is 7x7, so `top2%` and `最大` are the same operator; the 96 duplicate `最大`
  configurations are dropped, which is the 474 in the table.

## Reading the keys

These files were written during the work in Chinese and their data is published exactly
as recorded. Renaming keys after the fact would have meant editing every reference to them
in the documents and the report, which is a worse risk than a glossary. The vocabulary is
small. The one edit made for publication is in `p31_platform_leaderboard.json`, whose
provenance note now carries the leaderboard URL and drops the leaderboard position: a
position moves whenever anyone else submits, so it is not a property of the run this file
records. The measurements in that file are untouched.

In the two grid files, a cell key reads `backbone|basis|component|direction`, and the
component field uses four terms:

| Term | Meaning |
|---|---|
| `幂开` | signed power transform applied |
| `幂关` | signed power transform not applied |
| `均值` | global average pooling |
| `最大` | maximum over positions (identical to `top2%` on a 7x7 grid) |

`λ` is the shrinkage coefficient and `q` the instance-selection quantile. Directions are
written `c2→c1` for "fit on center 2, evaluate on center 1".

Field names inside the smaller files are also Chinese in places: `耗时秒` is elapsed
seconds, `名次变化` the number of rank changes, `格数` a count of cells, `A+落点` where
the A+ cells fall by backbone, `峰值下界` and `峰值上界` the bracket on peak memory.
`number_table_en.json` gives the English name of every key in `number_table.json`.
