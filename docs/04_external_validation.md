# External validation

## The question

How far do the internal results transfer to the data the challenge actually scores on?

## How it was measured

The same container, unchanged, was submitted to the challenge platform and evaluated on two
held-out sets: the RARE26 validation cohort and the RARE25 validation cohort. Neither was
seen during development. The platform reports the ranking metric, AUROC and AUPRC, each
with a 95% interval. The row these numbers were read from is the 2026-08-31 submission on
the Open Development Phase leaderboard,
https://rare26.grand-challenge.org/evaluation/open-development-phase/leaderboard/ ; that
page lists several submissions per entrant and its ordering changes as others submit, so
`results/p31_platform_leaderboard.json` records the row as read on that date rather than
relying on the page.

## Results

| Evaluation | PPV@90R at 1% | spec@90 | AUROC |
|---|---|---|---|
| Our cross-center, train c2 | 0.0787 | 0.894 | 0.9605 |
| Our cross-center, train c1 | 0.5214 | 0.992 | 0.9883 |
| RARE25 validation | 0.0151 [0.0106, 0.0345] | 0.407 | 0.8430 [0.7121, 0.9621] |
| RARE26 validation | 0.0152 [0.0104, 0.0306] | 0.411 | 0.7700 [0.6354, 0.8968] |
| Random ranking | 0.0100 | 0.100 | 0.5000 |

Intervals on the two validation rows are the challenge evaluator's own bootstrap. The cross-center rows carry none: what was recorded there is the interval on the paired difference against global average pooling, which is a different quantity.

## Is the pipeline working?

Yes, and this is worth checking before reading anything into the numbers. Inverting the
identity between the ranking metric and specificity gives an implied specificity at 90%
recall of 0.4110, and a binormal model at the observed AUROC predicts
almost exactly that. The two are consistent. Had the frame ordering or the label polarity
been wrong, AUROC would have sat at 0.5 rather than 0.7700.

## Conclusion

Performance falls a long way between our own cross-center evaluation and the held-out data.
This is not specific to this submission. A team in the previous edition of the challenge,
using a different architecture, reported cross-validation ROC-AUC of
0.9340 to 0.9600 falling to 0.7709
externally, with a ranking metric of 0.0112. Our figures are
0.7700 and 0.0152. The organizers of that edition
noted that positive predictive values remained low for most approaches.

The drop reproduces across teams, methods and editions, which makes it a property of the
task rather than a fault in any one pipeline.

## Limitations

We hold no images from the target distribution, so nothing here can be turned into a fix.
Every interval reported elsewhere in this repository is an in-domain interval and none of
them bounds performance on these sets. See `06_domain_shift_attribution.md` for what we could
and could not attribute the gap to.
