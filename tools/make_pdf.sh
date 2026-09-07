#!/usr/bin/env bash
# Regenerate RARE26_technical_report.pdf from REPORT.md, then check the two match.
# Needs: pandoc, xelatex, pdftotext, and the TeX Gyre Pagella font.
#
# Run from anywhere; paths below are relative to the repository root, not to tools/.
#
# The PDF is written to a temporary name and only becomes RARE26_technical_report.pdf
# after gate5 passes. An earlier version rendered straight to the final name and checked
# afterwards, so a failing run left a file that looked freshly built, carried today's
# timestamp, and had not passed its own check -- more dangerous than an obviously stale
# one, because the date says it is current. On failure the temporary file is removed and
# whatever was there before is left untouched: never replace a verified artifact with an
# unverified one.
set -euo pipefail
cd "$(dirname "$0")/.."

FINAL=RARE26_technical_report.pdf
TMP=tools/report_pdf.gen.pdf                 # tools/*.gen.* is gitignored

# `|| true` is load-bearing. Under `set -e` a failing command inside an EXIT trap becomes
# the script's exit status, so if the cleanup cannot remove its own scratch files -- a
# mounted or read-only working directory is enough -- the script prints "PDF matches
# REPORT.md." and then exits 1. Saying one thing and returning another is worse than
# either outcome alone: whoever reads the exit code and whoever reads the output reach
# opposite conclusions. Tidying up is not allowed to decide whether the check passed.
trap 'rm -f "$TMP" tools/report_pdf.gen.txt || true' EXIT

python3 tools/make_pdf_source.py REPORT.md tools/report_pdf.gen.md
pandoc tools/report_pdf.gen.md -o "$TMP" --pdf-engine=xelatex \
       -V mainfont="TeX Gyre Pagella" -V monofont="DejaVu Sans Mono"
pdftotext "$TMP" tools/report_pdf.gen.txt
python3 tools/gate5.py REPORT.md tools/report_pdf.gen.txt

mv "$TMP" "$FINAL"
echo "PDF matches REPORT.md. Wrote $FINAL."
