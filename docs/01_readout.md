# The read-out

## The question

The backbone produces a 7x7 map of 2048-dimensional features per image. The usual next step
is to average it and classify the result. Averaging spreads a small lesion across
49 positions. Does scoring each position separately and taking the strongest few work
better, and if so is the improvement real or a product of choosing among many options?

## How it was measured

Both give a single score per image, so they are directly comparable. The head is a
closed-form shrinkage discriminant fitted with the 49 positions as samples for the
within-class scatter. The only change under test is what happens after scoring: average the
map first, or score every position and take the top 2%, which on a 7x7 grid is the maximum.

Evaluation is true cross-center in both directions, with the paired bootstrap described in
`00_evaluation_protocol.md`.

## The decision rule

Adopted only if detectably positive in both directions. Registered before the comparison
was run.

## Results

| Direction | AUROC before / after | spec@90 before / after | PPV@90R at 1% before / after | residual false positives removed |
|---|---|---|---|---|
| train c2, test c1 | 0.9119 / 0.9605 | 0.679 / 0.894 | 0.0275 / 0.0787 | 66.9% |
| train c1, test c2 | 0.9720 / 0.9883 | 0.922 / 0.992 | 0.1045 / 0.5214 | 89.3% |

Every quantity in a row is a plug-in estimate on the same evaluation set, so the row is internally consistent: the specificity reproduces the PPV column through the prevalence identity. Detectability is assessed separately, by a paired bootstrap, and all six differences are detectable in both directions.

Five further checks, each of which could have removed it:

The gain sits in the hard positives and is near zero on the easy stratum, which is already
at ceiling. It improves the images that set the threshold rather than pushing easy cases
higher.

On an independent Barrett dataset where five experts delineated lesions separately, and
using a head fitted only on the challenge data, the highest-scoring cell falls inside the
expert consensus lesion 78.0% of the time against 16.7% for a random
cell. The lift grows with the level of agreement between experts.

A two-direction null control puts the joint chance rate at 0.7%,
measured over repeated label permutations rather than obtained by multiplying the
per-direction rates.

Repeating the entire component grid on a different layer gives 192 cells with
0 improvements; the only detectable movements there are reversions to averaging,
all negative.

The offline computation matches the container's own output to within
4.917e-07 per image with 0 rank changes.

## Conclusion

This is the one modification in the project that is established rather than merely
untested. It is also the only one that survived being attacked from five further
directions.

## Limitations

The comparison holds the backbone, the transform, the shrinkage and the fitting scope
fixed. It says that per-position scoring beats averaging under this configuration on this
data. It does not say the top 2% is the best pooling rule, and `02_backbones.md` shows the
preferred setting differs by backbone.
