# RARE26 — Frozen GastroNet DINO ResNet-50 with a per-position shrinkage discriminant

Submission code for the [RARE26 challenge](https://rare26.grand-challenge.org/)
(MICCAI 2026 EndoVis): detection of early neoplasia in Barrett's esophagus.
The method report is `REPORT.md`, also included as a PDF; `tools/make_pdf.sh`
regenerates that PDF from it and checks that the two agree.

Released under the MIT license, as required by challenge rule 7. The accompanying
method report is the one submitted under rule 6.

## What this is

A frozen backbone and a closed-form head. **No layer is trained.** The only learned
parameters are one 2048-dimensional discriminant vector and one mean vector, 16 KB in
total, shipped here as `container/resources/head.npz`.

The single design choice that matters is the read-out. Instead of global-average-pooling
the backbone's spatial map, every one of the 49 positions is scored with a shrinkage
Gaussian discriminant and the top 2% is taken:

```
frozen RN50 (GastroNet-5M, DINOv1)
  -> layer4 map, 7x7x2048            (no global average pooling)
  -> signed power transform, sign(x) * |x|^0.5
  -> subtract training mean
  -> closed-form shrinkage GDA; the 49 positions are the samples for the
     within-class scatter, shrinking toward (tr S / d) * I
  -> score every position, take the top 2% (the maximum on a 7x7 grid)
  -> logistic squash
```

The evaluation metric is positive predictive value at 90% recall, at 1% prevalence. It
depends only on the ordering of scores, so the final squash cannot change it.

## What is in here

| Path | Contents |
|---|---|
| `REPORT.md` | The method report submitted under rule 6. |
| `RARE26_technical_report.pdf` | The same report as a PDF. |
| `src/` | Grouping, head fitting, the classifier that produces every verdict in the tables, and a local implementation of the leaderboard metric. |
| `container/` | The submitted inference container, and the fitted head it ships. |
| `docs/` | One document per block of work: the question it asked, how it was measured, the rule written down before the numbers, the result, and the limitations. |
| `results/` | The result files the documents and the report are computed from, and the map from each number to its source. |
| `tools/` | Regenerating the report PDF from `REPORT.md` and checking the two agree, and checking that the published container source is a comment-only translation of the submitted one. |

The documents, in reading order:

| Document | What it covers |
|---|---|
| `docs/00_evaluation_protocol.md` | How comparisons were made and what "established" is allowed to mean here. |
| `docs/01_readout.md` | The one change that survived: per-position scoring instead of averaging. |
| `docs/02_backbones.md` | Eleven sets of pretrained weights, seven read-outs, and what none of them established. |
| `docs/03_assembly.md` | What happens when components are added one at a time under a strict threshold. |
| `docs/04_external_validation.md` | The challenge platform's numbers against our own. |
| `docs/05_what_we_got_wrong.md` | What went wrong that still matters for reading the numbers or repeating the work. |
| `docs/06_domain_shift_attribution.md` | How much of the gap simulated acquisition differences can account for, and on which key that question is answerable at all. |

## Backbone weights are not distributed here

The backbone is the GastroNet-5M ResNet-50 pretrained with DINOv1, obtained from the
Theta Vision Cortex pretrained-model listing under the **GastroNet-5M Dataset and Model
Weights - Unified Data Use Agreement (Academic & Commercial R&D) v1.0**. That agreement
does not permit redistribution, so the checkpoint is **not** in this repository.

To reproduce, request the weights from the provider under the same agreement, then point
the scripts at them:

```bash
export RARE26_BACKBONE="/path/to/RN50_GastroNet-5M_DINOv1.pth"
```

`container/resources/head.npz` is our own fitted head. It contains no backbone weights
and the backbone cannot be recovered from it.

## Reproducing

```bash
pip install -r container/requirements.txt scikit-learn scipy

# 1. Recover pseudo-patient groups so that near-duplicate frames of one examination
#    cannot straddle a split. Writes work/groups.npy.
python src/grouping.py

# 2. Fit the head. Selects lambda by 8 repeated grouped CV runs on pAUC(85-95),
#    then fits on all training images. Writes work/pack/head.npz.
python src/fit_head.py

# 3. Score. --demo runs a self-test on synthetic data and needs no inputs.
python src/scorer.py --demo
python src/scorer.py --csv your_scores.csv     # columns: label, score
```

Expects the challenge training images under `data/RARE25-train-data/`, laid out as the
challenge distributes them (`center_1|center_2` / `ndbe|neo`).

### Building the inference container

```bash
cd container
cp /path/to/RN50_GastroNet-5M_DINOv1.pth resources/backbone.pth
docker build --platform=linux/amd64 -t rare26-cpu .
```

The container reads one stacked `.tiff` or `.mha` from
`/input/images/stacked-barretts-esophagus-endoscopy/` and writes one score per frame, in
frame order, to `/output/stacked-neoplastic-lesion-likelihoods.json`.

Measured on a 384-image case, end to end from `docker run` so that container start-up
and model loading are included: about 16 s on a laptop CPU and 26 s on the evaluation
hardware, against a 600 s limit. Peak memory sits between 2 and 3 GB, established by
lowering the container limit until the process was killed.

## A note on the published source

Comments and log messages in `container/inference.py` were translated into English for
publication. The code that determines the numbers is unchanged from the version used to
build the submitted container. This is checked mechanically rather than asserted:

```bash
python tools/check_ast_identical.py ORIGINAL.py container/inference.py
```

The script strips docstrings, drops the literal segments of f-strings, and compares the
resulting syntax trees, reporting how many string constants differ so the edge of the
claim is visible.

## Citation

The weights carry a citation obligation. Section 4 of the data use agreement requires
citing the dataset and weights together with every scientific publication listed on the
provider's page:

1. Jong, M. R., Boers, T. G. W., Fockens, K. N., et al. (2025). GastroNet-5M: A
   Multicenter Dataset for Developing Foundation Models in Gastrointestinal Endoscopy.
   *Gastroenterology*. PII S0016-5085(25)05797-X. (The DOI printed on the provider's
   landing page does not resolve; the publisher's record gives this PII.)
2. Boers, T. G. W., Fockens, K. N., van der Putten, J. A., et al. (2024). Foundation
   models in gastrointestinal endoscopic AI: impact of architecture, pre-training
   approach and data efficiency. *Medical Image Analysis*, 98, 103298.
   doi:10.1016/j.media.2024.103298
3. Jong et al. (2025). Evaluation of an improved computer-aided detection system for
   Barrett's neoplasia in real-world imaging conditions. *Endoscopy*.
   doi:10.1055/a-2642-7584
4. Jong et al. (2025). The development and ex vivo evaluation of a computer-aided
   quality control system for Barrett's esophagus endoscopy. *Endoscopy*, 57(7),
   709-716. doi:10.1055/a-2537-3510
5. Jong et al. (2025). Impact of standard enhancement settings of endoscopy systems on
   performance of endoscopic artificial intelligence systems. *Endoscopy*, 57(6),
   602-610. doi:10.1055/a-2530-1845

## Declarations

**Intended use.** This is research software. It is **not a medical device**, it has not
been clinically validated, and it has not been tested in any clinical workflow, on any
prospective cohort of ours, or in any reader study. Section 11 of the weight provider's
agreement says the same of the pretrained weights, and nothing here should be read as a
claim of clinical readiness.

**Challenge data.** The training and validation images belong to the challenge organizers
and are distributed by them under their own terms. They are not redistributed here. No
image, no crop, and no per-image record appears in this repository: `results/` holds
aggregated statistics only. `src/` expects the images to be present locally, laid out as
the challenge distributes them.

**Backbone weights.** Covered by the GastroNet-5M agreement named above, which is free for
academic use and forbids redistribution. The checkpoint is not in this repository; the
submitted container carried a copy because the platform evaluates with the network
disabled and the submission format requires a self-contained image. Section 4 of that
agreement also imposes the citation obligation listed under Citation, which applies to
anyone who uses the weights, not only to us.

**What the license covers.** The MIT license above covers the code in this repository and
`container/resources/head.npz`, which is our own fitted head. It does not extend to the
backbone weights or to the challenge data, and it cannot: neither is ours to license.

**Numbers.** No number in `docs/` or in the method report was typed by hand. Each is
inserted by script from `results/number_table.json`, which names the source of every one of
the 442 values it holds. Most of those sources are files in `results/`; the rest are the
classifier in `src/verdict.py`, the fitting code in `src/`, or something outside this
repository — the challenge's own job page, the RARE25 summary paper, an internal working
note. `results/_untraceable_sources.txt` lists every key in that last group by name, so a
reader can see exactly which numbers they cannot check here and where each came from
instead. `results/number_table_en.json` gives the English name of every key. Where a
quantity was measured but its uncertainty was not, the tables say so and leave the interval
blank rather than borrowing one from a different estimator.

**Scope of the results.** The challenge scores reported here are the 2026-08-31 submission
on the Open Development Phase leaderboard,
https://rare26.grand-challenge.org/evaluation/open-development-phase/leaderboard/ , recorded
as read on that date in `results/p31_platform_leaderboard.json` because that page carries
several submissions per entrant and reorders as others submit. Performance drops
substantially between our own cross-center evaluation and the challenge's held-out data. This reproduces across teams, methods and
editions of this challenge, and is a property of the task rather than a fault in this
pipeline; the numbers are in `docs/04_external_validation.md` and what we could and could
not attribute the gap to is in `docs/06_domain_shift_attribution.md`. Every interval reported
anywhere in this repository is an in-domain interval. None of them bounds performance on
the closed evaluation sets.

**Author.** Single author. No funding, no institutional support, no competing interests.
