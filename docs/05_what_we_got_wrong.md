# What we got wrong

Not a confession list. This is the set of things that went wrong here and that still
matter to someone reading the numbers or repeating the work. Anything that was purely an
internal accident — a script that wrote to the wrong path, a label typed wrong in a working
file, a bookkeeping slip found the same afternoon — is left out, because knowing about it
would not change what you do.

Three groups: what changes how a number here should be read, what will cost you time if you
reproduce this, and what the metric itself did to us.

## What changes how a number here should be read

The letter classes used below (A+, A-, B+, B-, C, D, E) are defined in
`00_evaluation_protocol.md` and counted family by family in `07_verdict_counts.md`. The
README folds them into four plain groups; `better` there is A+ and B+ together, `worse` is
A- and B-, and `could not separate` is C and D.

**The verdict columns are AUROC classifications, and the rule is stricter than an early
draft of our own documentation said.** The seven-class table in `00_evaluation_protocol.md`
once stated the A+ condition as "at least one direction at or above the threshold". The
classifier requires both. The published counts were always produced by the code, so no
number moved, but the written rule described a weaker bar than the one applied. Under the
weaker rule the largest grid would read A+ 22 / A- 53 / B± 7 instead of 17 / 51 / 14. The
rule is now stated as the code implements it, and the code is published as `src/verdict.py`
so you do not have to take the prose for it.

**The grouping script in this repository did not reproduce the grouping the results were
built on, and nobody had checked.** Pseudo-patient groups decide every split and every
resampling unit in the evaluation, so they sit under all of it. `src/grouping.py` drew its
features through the deployment resize, original to 512 to 224; the cached features the
published grouping was actually built from went straight to 224. Same threshold, same
mutual-neighbor rule, same graph code — we checked that by running both implementations
on both feature sets and getting identical partitions each time — but the two resizes put
34 of the 3095 images, 1.1%, into different groups, because those images sit right at the
threshold. Neither resize is the correct one: grouping asks which frames are
near-duplicates of each other, which is a different question from what the model sees at
inference. The script now uses the resize the published results were built on and
reproduces them image for image. Before changing it we re-ran the one conclusion this
project actually rests on, per-position scoring against global average pooling, under both
groupings: detectably positive in both cross-center directions either way, so it does not
depend on the choice. That check held the shrinkage coefficient fixed, and the coefficient
had itself been selected under one of the two groupings, so it says the conclusion is
insensitive to the grouping, not that the whole pipeline is.

**The largest grid counts 65 comparisons of a configuration against itself.** In
`d1_all_backbones.json` the pooling axis includes `top 1 position` and `top 2% of
positions (k = 1)`, which on a 7x7 grid are the baseline operator itself. Their paired
difference is exactly zero in both directions at every shrinkage value, so 65 of the 616
cells carry six zeros and no information. All 65 fall in class C, which is the class for a
comparison the intervals rule out; a configuration compared with itself is not ruled out,
it was never a comparison. The published row therefore reads C 397 where the informative
count is 332; A+, A-, B+, B-, D and E are untouched, which is why no claim in the report
moves. We have not changed the published number, because one rule applied inconsistently
across families is worse than one rule applied openly, and the two grids that are
deduplicated say so in their own annotation. `07_verdict_counts.md` records the same thing
from the counting side.

**The domain-shift page described its adoption rule as one condition when three were
registered.** All three are in the script header that produced the numbers; the page
published the second and called it the criterion. The two it dropped were the two that
could reject, so the published rule was weaker than the one we ran under. No verdict
changes — nothing was adopted either way — but a page whose subject is protocol
discipline got its own protocol wrong, and that is the kind of error this report exists
to make findable.

**The domain-shift attribution reverses depending on which key you read it with, and only
one of the two readings is admissible.** We first computed it on AUROC alone and concluded
that acquisition differences are not the main driver. Read on the ranking metric, the same
perturbations account for 129.5% and 146.1% of the gap. Three causes that between them
exceed the whole gap are not a decomposition of it, which is what disqualifies the second
reading rather than supporting it. `06_domain_shift_attribution.md` states the conclusion
and shows both columns; the earlier one-key readings are not in this repository, but if you
compute either half on its own you will reach a conclusion we had to withdraw.

**One adoption rule in this project was half empty and we did not notice while writing it.**
The four candidate corrections in `06_domain_shift_attribution.md` were required to be "not
detectably worse" on two keys across two directions. In all eight cells the ranking metric
detects no difference at all, so that half of the rule can never reject anything. It reads
as a four-cell bar and is a two-cell bar. The verdicts stand — the AUROC half did reject
two candidates — but the rule is weaker than its description.

**A verdict was reported as "neither key could measure it" for a day when it was measured.**
A hand-written chain of conditions ended in a default branch, so a combination nobody had
enumerated came out with the least informative label. It landed on the strongest result in
that experiment. The label now comes from the classifier's exhaustive output, and the
default branch raises instead of returning.

**An earlier version of the classifier had no sign constraint.** It required both directions
to be detectable and large, but not to agree in sign, and so reported 43 of 55 cells as
established improvements when all 43 were negative. If you write your own two-direction
rule, this is the failure mode to guard first.

## What will cost you time if you reproduce this

**Section 1 named the wrong order statistic, and did so for the life of this report.** It said
that to reach 90% recall the threshold sits on the `ceil(0.9 * n_pos)`-th lowest positive. It sits
on the `n_pos - ceil(0.9 * n_pos) + 1`-th: the 7th lowest at 61 positives, the 10th at 97.
`ceil(0.9 * n_pos)` is the number of positives that must stay above the threshold, which is a count,
not a rank, and the sentence put the count in the rank's place. No number here moves: the scorer
reads the metric off an interpolated precision-recall curve and never indexes the sorted positives
at all. That is also why nothing caught it. Every gate in this repository compares one computed
quantity against another, and this was a sentence with no computed quantity behind it. Our own
working notes used the correct form throughout; the error appeared when the mechanism was written
out in English, and survived because the expression it names is a real quantity in the
neighboring sentence. Corrected 2026-09-08. The submitted method report does not contain it -- that document
names the order statistic without indexing it.

**The 49 positions of one image are not independent.** Counting each position as a sample
puts the ratio of samples to dimensions at 2.51, and moving to a wider feature map appears
to drop it to 0.057. Both figures are inflated by the same factor, because the 49
positions of one image carry far less information than 49 independent samples: the honest
ratio at the second setting is nearer 0.35. The head is fitted with the positions as
samples for the total scatter, grand-mean centered, which is the point of the design, but
any sample-size argument built on 49n is wrong by roughly a factor of five.

**Training and serving do not preprocess identically, and the difference is not free.**
Training resizes through PIL; the container uses `torch.nn.functional.interpolate` with
`antialias=True` because it has no PIL in the hot path. With the flag the two agree to
0.258/255 mean and 1/255 maximum. Without it, 1.358/255 and 81/255 — a different feature
distribution from the one the head was fitted on. If you rewrite the preprocessing, measure
this before trusting anything downstream.

**The documentation described the head's covariance as something the code does not
compute.** Five places said within-class scatter; the code forms the total scatter, centered
on the grand mean. The two differ by a rank-one term along the class-mean difference, so the
solved direction is identical up to a positive scalar and no published number moves -- but a
reader who knows discriminant analysis, reading the code against the prose, would conclude we
had made an error. No gate here could have caught it: every one of them checks whether a
number is right, and none checks whether a word is.

**A cached feature map is not the delivered pipeline's features.** We treated one as the
other for a while. The delivered path has two resize stages, original to 512 to 224, where
the cache went straight to 224, and the results differ by 25%. This page had that backwards
for a hundred lines while stating it correctly in the grouping entry above: two sentences on
one page, contradicting each other, and nothing computed was watching either of them.

**Do not compare layers under global average pooling.** Averaging dilutes by the number of
positions, so a shallower layer with a larger map loses for a reason that has nothing to do
with what it represents. Layer comparisons here are run under the read-out actually used.

**Match the sampling fraction across grids with different map sizes.** A control ran at 1/49
against 1/196 and the comparison meant nothing.

**Do not cut difficulty strata with the baseline's own scores.** It is circular with respect
to the baseline, which is usually the thing being tested.

**Timing must be measured on the real case size.** Our first deployment argument used the
16-image sample; a case is a file of 384 frames. Every number in it was correct and none was
about the quantity under discussion.

**EVC, the EndoVis 2015 Barrett dataset, is not a domain-shift target for this task.**
The delivered pipeline scores AUROC 0.9856 on it, higher than on our own cross-center split. We selected it to exhibit a shift
and it does not have one. It is a good localization check, which is what it is used for here.

**A color perturbation with no spatial term does not test an enhancement setting.** Our first
one had three global per-pixel degrees of freedom, while the work motivating the experiment
is about spatial enhancement. The published axes include sharpening and compression for that
reason.

**DINO's augmentations do not make the backbone invariant to color in any useful sense.** We
carried that as known. Measured, unsharp masking displaces the features by 49.5% of their norm
with essentially no change in AUROC. The features move a long way; the discriminant does not
use those directions.

**Get the license right before you build anything.** We attributed the weight license to the
wrong file in a set of eight, and then had the license name wrong as well. The correct one is
named in the README. The DOI printed on the provider's landing page does not resolve; the
publisher's record gives PII S0016-5085(25)05797-X.

## What the metric did to us

Every one of the above is downstream of one property: the ranking metric is a threshold
statistic read off a single order statistic of the positive scores, and at 1% prevalence its
value is then set by the far tail of the negatives. That makes it move a great deal in
response to almost anything, which is why the label-noise cost is one to two orders of
magnitude larger on it than on AUROC, why the attribution is not identifiable on it, why the
four-cell rule was half empty, and why almost nothing in this project could be resolved.

We derived that property in the first section of the report and then spent most of the
available time not acting on it. If we started again, the protocol would be built around it
from the first week rather than assembled around it afterwards.

**The specific thing not done was a power calculation, and the cost was a budget spent on
grid size.** Freezing the backbone is what made 1835 comparisons affordable, and that is a
real advantage, but it solves cost and not power. Power here is set by three things: the
number of positives, which is 158 and fixed; the size of the effect, which the data decides;
and whether the comparison is paired, which it is. **Running more cells raises none of them.**
It raises only the number of cells that come out detectable by chance. The practical
threshold, 0.0165, was in hand before the grid was run, and for most of what the grid
contained the expected effect was smaller than that -- which was knowable in advance, not
only in hindsight. The correct move was to run fewer comparisons, four families with one
question each, rather than to run the grid at finer resolution. This is a protocol defect
rather than a regret: it changed where the available time went.

## One thing we cannot fix

The method report submitted to the organizers spells one word the British way,
`neighbouring`, in the sentence that takes the frozen-encoder setting from a neighboring
low-data problem. The rest of this project is American English and the checker now catches
that form, but the submitted PDF is the submitted PDF and we are not going to reissue it
over a vowel. The copy in this repository is correct.

## One process note

Several checks in this project reported success without having examined anything: a
container verification that exited zero while the container engine was not running, a scanner
that reported all clear after matching no files, a rule that passed on a direction with
nothing in it to separate. Every gate in this repository is now run twice — once against a
deliberately broken input to prove it reports red, then once for real. The third one above,
the rule that passed on a direction with nothing in it to separate, was found that way rather
than by accident. If you use the checks here, run them that way
too; a gate that cannot report failure is worse than no gate, because its output is taken as
evidence.

Registering a rule before running the comparison turned out to do more than stop us
rewriting it afterwards. Writing it down means turning it into a condition something can
evaluate, and doing that is when we found that the baseline did not sit where we had
assumed. A rule kept in the head never has to be that specific.

The self test was then found broken twice, and neither time by running it. In one gate
the self test sat behind a branch that could never be taken, so the check that proves
that gate can report red had itself never run. In another the self test restored the
file it had deliberately damaged without pinning the line ending, which on Windows
rewrote every line of the report and left a change in the repository that had nothing to
do with the report; that is where an unexplained whole-file diff had been coming from.
Both were found by reading the code rather than by running it. A self test is a check
like any other, and nothing was checking it.
