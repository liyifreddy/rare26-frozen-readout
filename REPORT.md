# A frozen read-out for early Barrett neoplasia: one positive result, a set of null results, and a domain gap that reproduces

Yi Li
Independent researcher, Darmstadt, Germany
M.Sc. Computer Science, Technical University of Darmstadt, 2026
Code: https://github.com/liyifreddy/rare26-frozen-readout

## Summary

We report a submission to the RARE26 challenge, which asks for detection of early
neoplasia in Barrett's esophagus and ranks entries by positive predictive value at 90%
recall with prevalence fixed at 1%. The training set contains 158 positive
images, which rules out fine-tuning a large encoder, so we froze the backbone entirely
and worked on the layer above it. The only learned parameters are one discriminant
vector and one mean vector, 4096 numbers in total. One change earned
its place: scoring each of the 49 spatial positions separately and taking the top 2%,
rather than averaging the map first. It is detectably positive in both cross-center
directions on all three read-outs and survives five further checks, including an
external localization test against five independent expert delineations. Almost nothing
else was. Ten alternative backbones, seven read-outs, the choice of layer, and every
component combination we tried produced no configuration that is detectably better in
both directions, and the improvements that do exist all land on backbones other than the
one we ship. On the challenge validation set the pipeline reaches AUROC
0.7700 and PPV@90recall 0.0152, against a random
baseline of 0.0100 and our own cross-center AUROC of
0.9605 and 0.9883. A team in the
previous edition of this challenge, using a different architecture, reported the same
pattern and almost the same number: cross-validation ROC-AUC 0.9340 to
0.9600 falling to 0.7709 externally. We simulated
three acquisition differences and found they account for a small fraction of that gap.
The rest is not in the imaging. Most of what we learned is in the evaluation protocol
rather than in the method, so we describe it in more detail than the results it
supports, and we list the mistakes it failed to catch.

## How to read this report

Every number here is inserted by a script, not typed by hand. The repository holds the
table that maps each one to its source, together with the code that generates it. Most of
those sources are result files in the repository; the rest are the published classifier,
the fitting code, or something outside it, and the repository lists that last group by name
so you can see which numbers you cannot check there. Where a quantity was measured but its
uncertainty was not, the table says so and leaves the interval blank rather than borrowing
one from a different estimator.

---

## 1. The task, and what the metric actually measures

The task is binary. Given an endoscopic image of Barrett's esophagus, decide whether it
contains early neoplasia. The platform delivers one case as a single stacked file of
384 frames and expects one score per frame.

Ranking uses a single number: positive predictive value at 90% recall, with prevalence
fixed at 1%. Everything in this report follows from the shape of that number, so it is
worth writing it out. At fixed prevalence,

```
PPV = 0.9 pi / [ 0.9 pi + (1 - spec) (1 - pi) ],    pi = 0.01
```

where `spec` is specificity at the operating point where sensitivity is 90%. PPV is a
strictly increasing function of that specificity. The two cannot point in opposite
directions. They can only differ in how noisy they are.

That is the easy half. The harder half is where the operating point comes from. To reach
90% recall you place the threshold at the score of the `ceil(0.9 * n_pos)`-th lowest
positive. That is one order statistic of the positive scores, not an average over
anything. With 158 positives in the training set and fewer in any single
evaluation fold, that order statistic moves whenever a handful of hard positives move.

The prevalence then does the rest. At 1% prevalence, once the threshold is set, the value
of PPV is decided by how many negatives sit above it, which is the far tail of the
negative score distribution. A small shift in the threshold sweeps a lot of that tail.

So the ranking metric is a threshold statistic that reads off a single point, while AUROC
is an average over all positive-negative pairs. They are not two views of the same thing
at different resolutions. The following table gives the correspondence under a binormal
model with equal variances, and includes the random baseline.

| AUROC | implied spec@90 | implied PPV@90R at 1% prevalence |
|---|---|---|
| 0.50 | 0.100 | 0.0100  (random baseline) |
| 0.65 | 0.231 | 0.0117 |
| 0.77 | 0.406 | 0.0151 |
| 0.84 | 0.550 | 0.0198 |
| 0.93 | 0.790 | 0.0414 |
| 0.96 | 0.884 | 0.0726 |
| 0.99 | 0.978 | 0.2896 |

Two consequences run through the rest of this report. First, an AUROC that looks
respectable can sit on a PPV that is close to the random baseline. Second, anything that
disturbs a small number of hard positives will show up in the ranking metric long before
it shows up in AUROC. We report both numbers side by side everywhere, and when they
disagree we treat the disagreement as the result rather than choosing one.

---

## 2. The data, and what it is not

The public training set has 3095 images, of which 158 are positive,
collected from two centers. Center 1 contributes 2279 images with
61 positives; center 2 contributes 816 images with
97 positives.

Both centers are Dutch, both collections are retrospective, and the challenge
documentation states that they were acquired without a standardized imaging protocol.
The validation and test cohorts are different in three ways at once. They draw on twelve
centers rather than two. They include prospectively acquired images. And those
prospective images follow a standardized protocol, acquired by endoscopists specializing
in Barrett surveillance.

This matters more than a sentence in a limitations section. The strongest evaluation we
can build from the public data is to train on one center and test on the other, in both
directions. That measures robustness to the difference between two retrospective Dutch
collections. It does not measure robustness to the difference between a two-center
retrospective collection and a twelve-center partly prospective one. **The shift we can
validate is not the shift we are evaluated on.** Every internal number in this report
should be read with that sentence attached.

Labels are the second gap. The training annotations were produced without the involvement
of a specific expert group, while the prospective part of the evaluation data was acquired
by Barrett specialists. We did not have access to the evaluation labels, so we cannot
measure the difference directly. We can measure the scale of expert disagreement on a
comparable task: on an independent Barrett dataset where five experts delineated the same
lesions, the median pairwise intersection over union between two experts was
0.7047 across 500 pairs.

Finally, a note on quantity. 158 positives is the number that determines what
can and cannot be established here, and it appears again in section 5 when we describe how
wide the confidence intervals turn out to be.

---

## 3. Why the encoder is frozen

With 158 positive images, fine-tuning a large encoder is not the right use of
the data. The binding constraint is the quality of the representation, not the capacity to
fit. A network with tens of millions of free parameters and a few hundred positives will
find the training set long before it finds the disease.

We therefore froze the encoder completely and put the work above it. Nothing in the
backbone is trained. The learnable parameters are one discriminant vector and one mean
vector, 4096 numbers in total, about 16 KB on disk. This makes every
result in section 6 an experiment about the read-out and the scoring layer rather than
about optimization.

Two boundary conditions are worth stating, though neither is the reason for the choice.
The pretrained weights come with a data use agreement that permits academic research and
forbids redistribution, so they are declared but not shipped with our code. Compute was a
single laptop GPU, which rules out repeated pretraining runs but not the experiments we
actually ran, since the encoder is frozen and features are extracted once.

The design has a side effect that turned out to be useful. Because the encoder never
changes, every ablation is a change to a small closed-form computation on cached features.
That made it cheap to run each comparison in both cross-center directions, with paired
resampling, rather than once with a single split.

---

## 4. Related work

Three lines of prior work bear on this report. We use them to place our numbers rather
than to justify the method.

**The previous edition of this challenge.** RARE25 ran the same task with the same metric
and published a summary. Two facts from it matter here. The organizers note that
"although several methods achieved strong overall discriminative performance, positive
predictive values remained low for most approaches, emphasizing the intrinsic difficulty
of low-prevalence detection". And one team reported cross-validation ROC-AUC between
0.9340 and 0.9600 that fell to ROC-AUC
0.7709 and PPV@90recall 0.0112 on a separate
development set. The winning entry reached PPV@90recall 0.3200 on
the full closed test set, but a median of 0.0350 under
resampling at the intended class imbalance. We return to these numbers in section 8,
because our own results land on top of them.

**Label noise and the choice of metric.** Menon et al. prove that under class-conditional
label noise the corrupted AUC is a positive affine transform of the clean AUC, so the
ranking induced by any scorer is unchanged. They also state the limit of that result
directly: for measures other than balanced error that are optimized by thresholding the
class probability, one has to know the noise rates or the base rate in order to place the
threshold. Precision at a fixed recall is such a measure, and they do not analyze it.
Elkan and Noto give the corresponding correction for precision when positives are
contaminated in the positive-unlabelled setting. What is missing is not the theory but the
magnitude: how much does a fixed amount of label noise cost a fixed-recall precision
metric relative to what it costs AUC. Section 6 reports that measurement.

**Acquisition differences in endoscopic AI.** The provider of the pretrained weights has
published on the effect of endoscope enhancement settings on the performance of endoscopic
AI systems, and on the evaluation of a Barrett CADe system under real-world imaging
conditions. We take the mechanism from that work and test it directly in section 8, where
we perturb color, sharpening and compression and measure how much of our own gap each can
account for.


---

## 5. How the evaluation protocol was set

This section is longer than the results section it supports. That is deliberate. Most of
what we learned in this project is in the protocol rather than in the method.

**Both directions, always.** Every comparison is run twice: train on center 1 and evaluate
on center 2, then swap. A result in one direction is never adopted. This is not a
robustness flourish. In our data the two directions disagree often enough that
single-direction results are close to worthless, and we report below how often.

**Paired resampling.** Differences are estimated by a paired bootstrap that resamples cases
within patient groups and resamples both classes. Comparing two configurations on the same
resample removes the variance that dominates when each is bootstrapped separately.

**Grouping.** Consecutive frames of one examination are near duplicates. If they straddle a
split, the evaluation measures memorization. We group near-duplicate images before any
split, using mutual nearest neighbors with a cross-center constraint, so that one
examination cannot appear on both sides.

**Two keys, reported together.** AUROC and the ranking metric are reported side by side for
every comparison. AUROC is the lower variance estimate and we use it to screen. The ranking
metric is what decides adoption because it is what the leaderboard uses. When the two
disagree, we report both and treat the disagreement as the finding. Section 6 contains
several cases where reporting only one key would have converted a measured result into a
non-result, and one where it did.

**A signed verdict with seven classes.** Each comparison is classified from the two
directions together, not by eyeballing point estimates:

| Class | Meaning | Condition |
|---|---|---|
| A+ | established (improvement) | Both directions detectable and positive, and both at or above the threshold |
| A− | established (degradation) | Both directions detectable and negative, and both at or above the threshold |
| B+ | directional, below practical threshold | Both directions detectable and positive, at least one below the threshold |
| B− | directional, below practical threshold | Both directions detectable and negative, at least one below the threshold |
| C | ruled out | Both intervals lie wholly inside the threshold band |
| D | tested, not detected | Anything else |
| E | direction conflict | Directions disagree in sign, at least one detectable and large |

Threshold: |delta AUROC| of 0.0165, measured from a power curve on this data. Detectable means the paired bootstrap interval excludes zero.

The important detail is the sign constraint. An early version of this classifier required
only that both directions be detectable and large enough, without requiring them to agree
in sign. It labeled configurations that were reliably *worse* as established. That
mistake is easy to make and hard to see in a summary table, which is why the classifier is
a single function that every script calls rather than a rule each script applies.

**A detection threshold that was measured, not chosen.** The threshold for calling a
two-direction difference detectable is 0.0165 on the AUROC scale. It comes from a
power curve measured on this data, not from a convention.

**Pre-registration.** Before any grid was run, the decision rule for reading its output was
written down and dated: which quantities would be reported, what would count as adoption,
and what would be done if the result was ambiguous. The rules are in the repository with
their timestamps. Writing them afterwards would have let the numbers choose the rule.

**No argmax, and the control that justifies it.** We never take the best cell of a grid.
The reason is measured rather than assumed. We ran one strictly nested search in which an
inner loop enumerated 120 configurations per backbone per direction and
kept the best, and an outer fold that the inner loop never saw reported the result. On the
ranking metric, 9 of 22 paired cells were detectably worse
and 1 was better. The mechanism is ordinary: the maximum of N noisy
estimates is inflated by about sigma times the square root of 2 ln N, which is
3.1 sigma at N = 120, far above anything this dataset
can resolve.

**What the protocol cannot do.** All of the above controls selection and noise. None of it
controls the gap described in section 2. A protocol can only be honest about the
distribution it samples from, and ours samples from two retrospective Dutch centers.

---

## 6. What we tried, and what each thing did

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

The table above is the whole record. This section says what the rows mean.

**One change survived.** Replacing global average pooling with per-position scoring
followed by top-2% pooling is the only modification that is detectably positive in both
directions on all three read-outs. Under true cross-center evaluation it moves AUROC by
+0.0486 and +0.0163, specificity at 90%
recall by +0.2069 and +0.0682, and the ranking
metric by +0.0512 and +0.4169. Residual false
positives at 90% sensitivity fall by 66.9% and
89.3%.

We then tried to break it five more ways. The gain concentrates in the hard positives and
is near zero on the easy stratum, which is at ceiling, so it improves the images that set
the threshold rather than pushing easy cases higher. On an independent Barrett dataset
where five experts delineated lesions separately, the highest-scoring cell falls inside the
expert consensus lesion 78.0% of the time against 16.7% for a random
cell, and the lift grows with the level of expert agreement. Repeating the entire component
grid on a different layer gives 192 cells with 0 improvements. A
two-direction null control puts the joint chance rate at 0.7%, measured
rather than obtained by multiplying the per-direction rates. And the offline reproduction
matches the container's own output to within 4.917e-07 per image with
0 rank changes.

**Component improvements exist, and none of them is on the backbone we ship.** Across
every family in Table 3, 61 cells improve in both directions. All but
1 of them are on a ViT, and the exception is on out-of-domain CNN
weights. On the delivered backbone the count is 0. Ten alternative
backbones, seven read-outs and the choice of layer produced no configuration that is
detectably better than the delivered one in both directions. That is a statement about
this dataset as much as about the alternatives: at 61 and
97 positives the paired intervals on the ranking metric are wider than
the differences being tested.

**The two keys disagree often enough to matter.** In the largest grid, the number of
cells where AUROC and the ranking metric point in incompatible directions is
86 out of 474. A protocol that reports one key would present
about one comparison in five as settled when it is not. This is the same
effect described in section 1, seen from the other side: the two numbers summarize
different things, and at this sample size the difference is not academic.

One family stands out for being decisive rather than inconclusive. Modeling the normal
class alone and scoring by distance from it, rather than fitting a discriminant between
the two classes, is detectably worse in both directions in 40 of
44 cells. With 158 positives it is tempting to treat the task
as anomaly detection; on this data that choice costs a great deal, and unlike most of
our comparisons the cost is measurable.

**The assembly procedure is determined by where it starts.** Building the configuration one
component at a time, with each component required to clear the pre-registered
two-direction threshold, leaves every one of 11 backbones exactly where it
began, from either starting point. The number of backbones on which the two starting points
converge is 0. We report this as a negative result about the
procedure, not as support for the configuration we happened to start from.

**Label noise costs the ranking metric one to two orders of magnitude more than it costs
AUC.** We flipped labels on the training set at increasing rates, in two ways: uniformly
within each class, which is the setting Menon et al. analyze, and preferentially on the
hardest positives, which is closer to how annotators actually disagree. Training used the
flipped labels; evaluation always used the true ones. At a 5% flip rate the ranking metric
falls by 30.5% to 46.0% while AUROC
falls by 0.3% to 2.5%, a ratio of
about 19 times to about 106 times across four curves. This is the
empirical complement to the theory cited in section 4, and it is the clearest single
demonstration of the point made in section 1.


---

## 7. What we submitted

The delivered pipeline is the frozen backbone, the per-position discriminant, and top-2%
pooling. In full:

| Pipeline step | What it does | Where the evidence is |
|---|---|---|
| Read the stacked file | One .tiff or .mha per case, N frames of 512x512 | `p28_384.json`, `p29_platform.json` |
| Resize 512 then 224 | Two downscales, both anti-aliased, matching the training path | `t7_train_serve.json`, `audit_2stage.json` |
| Frozen RN50 layer4 | GastroNet-5M DINOv1 weights, no fine-tuning, 7x7x2048 kept | `d1_all_backbones.json`, `r4_layer.json` |
| Signed power transform | sign(x) times \|x\|^0.5, applied before the head | `e3_basis_component.json` |
| Shrinkage discriminant | 49 positions as samples for the within-class scatter, lambda by grouped CV on pAUC(85-95) | `lambda_paired.json`, `lambda_endpoint.json` |
| Top 2% pooling | Score every position, take the maximum on a 7x7 grid | `p23_cross_confirm.json`, `c1_pooling_ops.json` |
| Localization check | Highest-scoring cell against five-expert consensus on an external set | `r9_evc_loc.json` |
| Logistic squash | Monotone, so it cannot change the metric | `scorer.py --demo` self-test 1 |
| Container output | One score per frame, in frame order | `p29_platform.json` |

The shrinkage coefficient is selected by repeated grouped cross-validation on partial
AUROC, and the final head is fitted on all images from both centers. Deployment is a
CPU-only container. One case is one file of 384 frames with a
600.0 second limit; measured end to end from container start, including model
loading, a case takes 15.8 seconds on a laptop CPU and
26.0 seconds on the evaluation hardware
(ml.r7i.large (2 vCPU, 16 GB, no GPU)). Peak memory lies between 2 GB and
3 GB against 16 GB configured.

The container was verified by reloading the packaged image, running it with the network
disabled, and comparing its output to the offline computation. On the platform itself, the
same stack scored through the platform's own ingestion produced 0 rank
changes against the local run, with a Spearman correlation of 1.0000.

The weights themselves are not ours to hand out. They are covered by the *GastroNet-5M
Dataset and Model Weights – Unified Data Use Agreement (Academic & Commercial R&D)
v1.0*, which is free for academic use and forbids redistribution. The submission
container carries a copy of the file, because the evaluation runs with the network
disabled and the challenge submission format requires a self-contained image. Our public
repository does not. Anyone reproducing this work obtains the same file from the
provider's pretrained-model listing at
`https://cortex.thetavision.nl/dataset-provider/listing/2/`, accepts the agreement, and
places it at the path the repository documents. That listing covers eight weight files
under one agreement; ours is the second, ResNet-50 pretrained with DINOv1 on GastroNet-5M.
No layer of it is fine-tuned.

---

## 8. What happened on the held-out data

| Evaluation | PPV@90R at 1% | spec@90 | AUROC |
|---|---|---|---|
| Our cross-center, train c2 | 0.0787 | 0.894 | 0.9605 |
| Our cross-center, train c1 | 0.5214 | 0.992 | 0.9883 |
| RARE25 validation | 0.0151 [0.0106, 0.0345] | 0.407 | 0.8430 [0.7121, 0.9621] |
| RARE26 validation | 0.0152 [0.0104, 0.0306] | 0.411 | 0.7700 [0.6354, 0.8968] |
| Random ranking | 0.0100 | 0.100 | 0.5000 |

Intervals on the two validation rows are the challenge evaluator's own bootstrap. The cross-center rows carry none: what was recorded there is the interval on the paired difference against global average pooling, which is a different quantity. The two validation rows are the 2026-08-31 submission on the Open Development Phase leaderboard, https://rare26.grand-challenge.org/evaluation/open-development-phase/leaderboard/ , recorded as read on that date because the page carries several submissions per entrant and reorders as others submit.

On the challenge validation set the pipeline scores AUROC 0.7700 with a
95% interval of [0.6354, 0.8968], and
PPV@90recall 0.0152 against a random baseline of
0.0100. On the RARE25 validation set the same container scores AUROC
0.8430 and PPV@90recall 0.0151. Our own true
cross-center AUROC is 0.9605 and
0.9883.

The first thing to check is whether the pipeline is working at all. It is. Inverting the
identity of section 1 gives an implied specificity at 90% recall of
0.4110, and a binormal model with AUROC 0.7700
predicts almost exactly that value. The two numbers are consistent with each other, and
both are well above the random baseline. Had the frame ordering or the label polarity been
wrong, AUROC would have sat at 0.5.

The second thing is that this is not specific to us. The team quoted in section 4 reported
cross-validation ROC-AUC of 0.9340 to 0.9600 and an
external ROC-AUC of 0.7709 with PPV@90recall
0.0112. Our figures are 0.7700 and
0.0152. The drop reproduces across teams, methods and editions, which
makes it a property of the task rather than a fault in any one pipeline.

We then tried to attribute the gap. Three acquisition axes were simulated on the test
side while the head stayed fitted on unperturbed training data: color and illumination,
unsharp masking, and compression artifacts. Each was pushed well past any realistic
setting.

The result depends on which key you read it with, and the disagreement is itself
informative. On AUROC, at realistic magnitudes the three axes together account for about
15.7% of the gap in one direction and 0.9% in the other,
and even at implausible strength color alone accounts for at most
28.8% and 8.1%. On the ranking metric the same
calculation returns 129.5% and 146.1%.

We do not read the second pair as showing that imaging explains half the gap. The
ranking metric responds this strongly to any perturbation, which is the property
established in section 1 and measured again in section 6, and on the main metric the
three shares sum to more than the whole, which is direct evidence that they are not a
decomposition. A quantity that moves a great deal in response to everything cannot
attribute anything to one cause. The attribution is therefore identifiable on AUROC and
not identifiable on the ranking metric, and what it says on AUROC is that these three
acquisition differences are not the main driver. That conclusion carries the caveat that
AUROC is the less sensitive of the two keys, which is why we state it as a bound rather
than as a decomposition.

A measurement taken alongside it points the same way. Unsharp masking displaces the
features by 49.5% of their norm while changing AUROC by
-0.0013 and -0.0036. The features move a long way
and the score does not follow. Measured directly, the fraction of the discriminant's
energy lying in the illumination subspace is 0.2% and
0.2%.

On the evidence that is identifiable, what remains is not imaging. Section 2 named the two candidates we cannot test: the
annotation was produced by different people under a different protocol, and the case mix
spans twelve centers with a prospective component rather than two retrospective
collections. Neither is something a pre-processing step can repair, and we hold no images
from the target distribution with which to learn one.

We also tested four modules intended to buy robustness to acquisition differences. Two are
detectably worse in one direction. The other two are not detectably worse on either key,
but their point estimates on the ranking metric are negative in both directions, and the
intervals are wide enough that "not detectably worse" carries very little information here:
across eight cells, the number in which the ranking metric detects any difference at all is
0. We did not adopt any of them. Their code and their numbers are
in the repository.

---

## 9. What we would do differently

**Get one measurement from the target distribution before choosing the question.** We spent
most of the available time on backbones, read-outs and component combinations, all
validated on a split between two retrospective Dutch centers. The first number from the
platform showed that the split we were validating on was not the split we were being
scored on. Had that number arrived in the first week, the work would have gone into the
question of what changes across centers rather than into which frozen encoder to use.

**Treat the metric as a threshold statistic from the start.** Section 1 states the identity
we used throughout, but we derived its consequences late. The single order statistic at the
heart of the metric explains the label-noise result, the size of the confidence intervals,
and why almost nothing we tried could be distinguished. A protocol built around that fact
from day one would have set different thresholds and asked for different sample sizes.

**Build gates that can fail.** Six checks in this project reported success without having
examined anything: a verification script that exited zero when the container engine was not
running, a repository scanner that reported all clear after matching no files, a placeholder
check that recognized one of the two markers actually present in the text, a registration
block that wrote nothing and exited zero, an adoption rule that passed on a direction with
nothing in it to separate, and a check that read its own success as failure because the
command it used prints a matching line for negation rules too. The first four were found by
accident. The last two were found on purpose, once we started running every gate twice: once
against a deliberately broken input to prove it reports red, then once for real. A gate that
cannot report failure is worse than no gate, because it is mistaken for evidence. The errors
from this project that still matter to a reader are in the repository at
`docs/05_what_we_got_wrong.md`.

**Write the reading rule before the numbers.** This one worked, and it is the practice we
would keep unchanged. Every grid in this project has a dated note stating what would count
as adoption before the grid was run. On more than one occasion the result was tempting and
the note was the only thing standing between us and a decision the data did not support.

---

## Declarations

**Intended use.** The pretrained weights are licensed for research and development only.
Section 11 of the agreement states that they are not a certified medical device and have
not been clinically validated. Nothing in this report is a claim of clinical readiness.
The system was built for a challenge, fitted on challenge training data, and evaluated on
challenge validation data; it has not been tested in any clinical workflow, on any
prospective cohort of our own, or by any reader study.

**Data.** The training and validation images belong to the challenge organizers and are
not redistributed here. No image from the challenge data appears in this report or in the
public repository.

**Code and numbers.** The code, the fitted head, the classifier that produces every verdict
in these tables, the pre-registered reading rules, and the result files are at
https://github.com/liyifreddy/rare26-frozen-readout under the MIT license. No number here
was typed by hand; each is inserted by script from a table that names its source. Most of
those sources are result files in that repository. The rest are the published classifier,
the fitting code, or something outside it — the challenge's own job page, the RARE25 summary
paper, an internal working note — and the repository lists those keys by name so a reader
can see which numbers they cannot check there. The pretrained weights are excluded, for the
reason given in section 7.

**Author and funding.** Single author. No funding, no institutional support, and no
competing interests.

---

## References

1. Jong, M. R., Boers, T. G. W., Fockens, K. N., et al. (2025). GastroNet-5M: a
   multicenter dataset for developing foundation models in gastrointestinal endoscopy.
   Gastroenterology. PII S0016-5085(25)05797-X.
2. Boers, T. G. W., Fockens, K. N., van der Putten, J. A., et al. (2024). Foundation
   models in gastrointestinal endoscopic AI: impact of architecture, pre-training approach
   and data efficiency. Medical Image Analysis, 98, 103298.
   doi:10.1016/j.media.2024.103298
3. Jong, M. R., van Eijck van Heslinga, R. A. H., Kusters, C. H. J., et al. (2025).
   Evaluation of an improved computer-aided detection system for Barrett's neoplasia in
   real-world imaging conditions. Endoscopy. doi:10.1055/a-2642-7584
4. Jong, M. R., Jaspers, T. J. M., van Eijck van Heslinga, R. A. H., et al. (2025). The
   development and ex vivo evaluation of a computer-aided quality control system for
   Barrett's esophagus endoscopy. Endoscopy, 57(7), 709-716. doi:10.1055/a-2537-3510
5. Jong, M. R., Kusters, C. H. J., van Bokhorst, Q. N. E., et al. (2025). Impact of
   standard enhancement settings of endoscopy systems on performance of endoscopic
   artificial intelligence systems. Endoscopy, 57(6), 602-610. doi:10.1055/a-2530-1845
6. RARE25 challenge organizers (2026). Development and evaluation of CADe systems in a
   low-prevalence setting. arXiv:2604.11171.
7. Menon, A. K., van Rooyen, B., Ong, C. S., Williamson, R. C. (2015). Learning from
   corrupted binary labels via class-probability estimation. ICML.
8. Elkan, C., Noto, K. (2008). Learning classifiers from only positive and unlabeled data.
   KDD.

References 1 to 5 are required by section 4 of the data use agreement covering the pretrained weights, which asks that the dataset and every publication listed on the provider's page be cited.
