# Evaluation protocol

## The question

Which comparisons in this project are trustworthy, and on what basis? The dataset has
158 positive images across two centers. At that size most differences are not
resolvable, so the protocol has to be able to say "we could not tell" as often as it says
anything else.

## How it was measured

Every comparison runs twice: train on center 1 and evaluate on center 2, then swap. A
result in one direction is never adopted.

Differences are estimated by a paired bootstrap. Cases are resampled within patient groups
and both classes are resampled. Two configurations are compared on the same resample, so
the shared variance cancels.

Consecutive frames of one examination are near duplicates. `src/grouping.py` groups them
using mutual nearest neighbors with a cross-center constraint, before any split is made,
so that one examination cannot appear on both sides.

Two read-outs are always reported together: AUROC and the ranking metric, which is
positive predictive value at 90% recall with prevalence fixed at 1%.

## The decision rule

Written before each grid was run, and dated. The rule assigns one of seven classes from the
two directions taken together.

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

Two details carry most of the weight. The classifier requires the two directions to agree
in sign, not merely to be detectable; without that constraint it labels reliably worse
configurations as established. And the threshold, 0.0165 on the AUROC scale, comes
from a power curve measured on this data rather than from convention.

We never take the best cell of a grid. The reason is measured: in one strictly nested
search the inner loop enumerated 120 configurations per backbone per
direction and kept the best, and an outer fold that the inner loop never saw reported
9 of 22 paired cells as detectably worse against
1 better. The maximum of N noisy estimates is inflated by about sigma
times the square root of 2 ln N, which is 3.1 sigma at N =
120.

## What this buys

Comparisons that survive both directions with agreeing signs are the only ones this report
states as findings. Everything else is reported as measured but not resolved, which is a
different statement from "no effect" and is kept distinct throughout.

## What it does not buy

The protocol controls selection and sampling noise. It says nothing about the difference
between the distribution we sample and the distribution the challenge evaluates on. Both
of our centers are Dutch, retrospective, and acquired without a standardized protocol; the
evaluation cohorts span twelve centers and include prospectively acquired images. No amount
of internal rigor reaches across that gap. See `04_external_validation.md`.
