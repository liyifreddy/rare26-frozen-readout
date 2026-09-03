#!/usr/bin/env bash
# Regenerate RARE26_technical_report.pdf from REPORT.md, then check the two match.
# Needs: pandoc, xelatex, pdftotext, and the TeX Gyre Pagella font.
#
# Run from anywhere; paths below are relative to the repository root, not to tools/.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 tools/make_pdf_source.py REPORT.md tools/report_pdf.gen.md
pandoc tools/report_pdf.gen.md -o RARE26_technical_report.pdf --pdf-engine=xelatex \
       -V mainfont="TeX Gyre Pagella" -V monofont="DejaVu Sans Mono"
pdftotext RARE26_technical_report.pdf tools/report_pdf.gen.txt
python3 tools/gate5.py REPORT.md tools/report_pdf.gen.txt
echo "PDF matches REPORT.md."
