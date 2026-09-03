# What we got wrong

Not a confession list. This is the set of things that went wrong here and that still
matter to someone reading the numbers or repeating the work. Anything that was purely an
internal accident — a script that wrote to the wrong path, a label typed wrong in a working
file, a bookkeeping slip found the same afternoon — is left out, because knowing about it
would not change what you do.

Three groups: what changes how a number here should be read, what will cost you time if you
reproduce this, and what the metric itself did to us.

## What changes how a number here should be read

**The verdict columns are AUROC classifications, and the rule is stricter than an early
draft of our own documentation said.** The seven-class table in `00_evaluation_protocol.md`
once stated the A+ condition as "at least one direction at or above the threshold". The
classifier requires both. The published counts were always produced by the code, so no
number moved, but the written rule described a weaker bar than the one applied. Under the
weaker rule the largest grid would read A+ 22 / A− 53 / B± 7 instead of 17 / 51 / 14. The
rule is now stated as the code implements it, and the code is published as `src/verdict.py`
so you do not have to take the prose for it.

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

**The 49 positions of one image are not independent.** Treating them as samples makes the
ratio of samples to dimensions look like 2.51 falling to 0.057 across a change that in
effect moves it to 0.35. The head is fitted with the positions as samples for the
within-class scatter, which is the point of the design, but any sample-size argument built
on 49n is wrong by roughly a factor of five.

**Training and serving do not preprocess identically, and the difference is not free.**
Training resizes through PIL; the container uses `torch.nn.functional.interpolate` with
`antialias=True` because it has no PIL in the hot path. With the flag the two agree to
0.258/255 mean and 1/255 maximum. Without it, 1.358/255 and 81/255 — a different feature
distribution from the one the head was fitted on. If you rewrite the preprocessing, measure
this before trusting anything downstream.

**A cached feature map is not the delivered pipeline's features.** We treated one as the
other for a while. The cache had two resize stages where the delivered path has one, and the
results differ by 25%.

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

**EVC is not a domain-shift target for this task.** The delivered pipeline scores AUROC
0.9856 on it, higher than on our own cross-center split. We selected it to exhibit a shift
and it does not have one. It is a good localization check, which is what it is used for here.

**A color perturbation with no spatial term does not test an enhancement setting.** Our first
one had three global per-pixel degrees of freedom, while the work motivating the experiment
is about spatial enhancement. The published axes include sharpening and compression for that
reason.

**DINO's augmentations do not make the backbone invariant to color in any useful sense.** We
carried that as known. Measured, sharpening displaces the features by 0.4952 of their norm
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

## One process note

Several checks in this project reported success without having examined anything: a
container verification that exited zero while the container engine was not running, a scanner
that reported all clear after matching no files, a rule that passed on a direction with
nothing in it to separate. Every gate in this repository is now run twice — once against a
deliberately broken input to prove it reports red, then once for real — and two of the six
were found that way rather than by accident. If you use the checks here, run them that way
too; a gate that cannot report failure is worse than no gate, because its output is taken as
evidence.
