# What we got wrong

This is the list of errors found during the project, grouped by kind. It carries no total.
The list grew at every audit — the last one added eleven entries and corrected the count in
this very document — so any number written here would be wrong by the next pass, and a
document about accuracy is the worst place to keep a figure that goes stale.

None of them was an arithmetic error. Every computed result, recomputed independently from
the stored files, matched. The errors are in the layer between a number and a sentence
about it, and in the machinery built to catch errors.

## Kind 1: a gate that cannot fail

The verification script for the delivered container exited zero and printed plausible
timings while the container engine was not running. Every command inside it had failed. It
had been run once in that state and that run was recorded as a pass.

The repository scanner reported both blocking categories clear after matching zero files.
Its directory list was hard-coded and did not include the directory it was run against.

The placeholder check searched for one of the two markers actually present in the text, so
a document containing `[TO BE FILLED]` was reported as fully filled.

A block that registers derived values wrote nothing, because the values it derived from had
not been registered yet, and exited zero.

An adoption rule passed on a direction whose measured sequence was constant. There was
nothing there to separate, and the rule said yes.

The check that the fitted head is not excluded from the repository read the output of
`git check-ignore -v`, which prints a matching line for a negation rule as well. A negation
rule means "do not ignore", so the check read its own success as failure. When that was
fixed the check became unfalsifiable instead: once a file is tracked, ignore rules no
longer apply to it, so nothing that could be added to the ignore file would make the check
fail. Both halves were found by running the gate's self-test, not by running the gate.

The shape is the same every time: a check whose failure path is unreachable. It is worse
than no check, because its output is taken as evidence.

## Kind 2: reporting one key when two were measured

A candidate improvement of +0.005 was rejected using the leaderboard's marginal interval,
which is not the interval for a paired difference.

A translated table dropped the column carrying the AUROC verdict. Four configurations that
are detectably worse on AUROC became "not detected".

The domain-shift attribution was computed on AUROC alone, which is the one instrument that
hides damage at the operating point. Reading the same data on the ranking metric reversed
the conclusion, and settling which reading holds took another round.

A four-cell adoption rule required a candidate to be not detectably worse on two keys in
two directions. In all eight cells the ranking metric detects no difference at all, so that
half of the rule can never reject anything. "Passes all four cells" was half empty, and the
rule had been written that way on purpose, by us, without noticing.

Each time the direction was the same: a measured negative result became a non-result.

## Kind 3: a category that swallows the unenumerated case

Stratified evaluation reported AUROC 0.0000 where a stratum held only one class. Read
quickly, that says "no shortcut here".

A hand-written chain of conditions ended in a default branch. A comparison that is
detectably worse on AUROC in both directions came out labeled "neither key could measure
it", and was reported that way for a day. It was the strongest result in that experiment.

The verdict classifier, in its first version, required both directions to be detectable and
large but not to agree in sign. It labeled reliably worse configurations as established:
43 of 55 cells reported as improvements, all 43 negative.

The second of these happened inside the gate built to prevent the third.

The fix was to derive the label from the classifier's own exhaustive output rather than
from a chain, and to remove the default branch so that an unenumerated combination raises.

## Kind 4: measuring something other than what was named

This is the hardest kind to catch, because nothing is computed incorrectly.

A ratio of samples to dimensions was reported as falling from 2.51 to 0.057. The 49
positions of one image are not independent; the effective ratio is 0.35.

Layers were compared under global average pooling, which dilutes by the number of
positions. A shallower layer had to lose, whatever it contained.

A control's sampling fraction was left unmatched across two grids, 1/49 against 1/196.

Difficulty strata were cut using the baseline's own scores, which is circular with respect
to the baseline.

A cached feature map was treated as the delivered pipeline's features. The delivered path
has one stage where the cache had two, and they differ by 25%.

A deployment timing argument was built on a 16-image sample when the time limit applies to
a file of 384. Every number in it was correct and none was about the quantity under
discussion.

An external dataset was chosen as a domain-shift target. Measured, the pipeline scores
AUROC 0.9856 on it, higher than on our own cross-center split, so it could not exhibit the
effect it was selected to test.

A color-shift hypothesis was tested with a perturbation that has three global per-pixel
degrees of freedom and no spatial term, while the paper motivating the hypothesis is about
spatial enhancement settings.

Self-checks cannot catch this kind. They verify that a computation is correct, not that it
is the right computation. The only defense we found is to write, in the registration for
each experiment, one sentence naming what is being measured and whether it is the same
quantity the motivation refers to.

## Kind 5: a fact asserted from memory

A row labeled "re-checked" pointed at a re-check that never happened; the numbers in it
came from the earlier run.

A label reading `c2→c1` named a transfer that never happened. It was a within-center
out-of-fold split.

Two absolute cross-center AUROC figures were taken from the first table in a script's
header, where they are two different backbones' minimum values, not one pipeline's scores.

"DINO's augmentations make the backbone invariant to color" was carried forward as
something known. Measured, the features move by 0.4952 of their norm.

A license was attributed to the wrong file in a set of eight, and the license name itself
then turned out to be wrong as well.

A DOI printed on a provider's landing page was carried forward without being resolved. It
returns 404.

The seven-class table in this repository had its class names generated from the classifier
and its Condition column typed by hand. The hand-typed part stated the A+ rule as "at least
one direction at or above the threshold" where the code requires both. The table had been
described as generated rather than transcribed, and the generated half was the half nobody
needed to check.

The rule that followed: a fact with a source is a key with a source, exactly like a number.
License names, rule quotations, deadlines and instance types are not typed into prose. And
when something is described as generated, say which part of it is generated.

## What the pattern says

Two of these five kinds are errors about the subject matter. The other three are errors in
the machinery. That distinction turned out to matter more than the count: an error about
the subject matter gets caught the next time someone looks at the number, while an error in
the machinery stops the looking from working.

The expensive ones all happened inside a safeguard. The default branch was in the gate
built to stop the sign error. The misread `git check-ignore` was in the gate built to stop
a file from being excluded. The hand-typed condition was in the table whose selling point
was that it was generated. Attention goes to the thing being guarded against, and the guard
itself gets built quickly.

Three rules came out of this and are in force in the code here:

* Any step whose job is to produce N things must assert that it produced N things.
* Any gate must be shown to fail before its passing is used as evidence. Every gate in this
  project is now run twice: once against a deliberately broken input to prove it reports
  red, then once for real.
* Any claim that something is generated rather than written must say which part.

## What this list is for

A repository that reports only its successes tells you nothing about how much to trust the
rest of it. Every result here was produced by a process that made these mistakes and found
them. That is the relevant context for reading the numbers, and it is not available
anywhere else.
