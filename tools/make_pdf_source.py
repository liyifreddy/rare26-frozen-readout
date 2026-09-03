# -*- coding: utf-8 -*-
"""Turn REPORT.md into the LaTeX-flavored markdown that pandoc renders to the PDF.

Two constructs need care, and both bit us before they were understood:

* pandoc treats everything between a raw `\\begin{X}` and `\\end{X}` as one raw LaTeX
  block and stops parsing markdown inside it. Since `%` starts a comment in LaTeX, an
  abstract wrapped that way silently loses every percent sign: "90% recall" renders as
  "90recall". The fix is to emit one-token macros, `\\babstract` and `\\eabstract`, which
  pandoc passes through without swallowing what lies between them. The same applies to
  the landscape page around the wide table.
* The experiment-family table has thirteen columns and does not fit a portrait page, so
  it gets its own landscape page.

Usage:
    python tools/make_pdf_source.py REPORT.md out.md
"""
import io
import sys

HEADER = r"""---
title: "%(title)s"
author: |
  | Yi Li
  | Independent researcher, Darmstadt, Germany
  | M.Sc. Computer Science, Technical University of Darmstadt, 2026
  | Code: <https://github.com/liyifreddy/rare26-frozen-readout>
date: "September 2026"
documentclass: article
fontsize: 10pt
geometry: "a4paper,left=2.4cm,right=2.4cm,top=2.4cm,bottom=2.6cm"
colorlinks: true
linkcolor: black
urlcolor: "blue"
header-includes: |
  \usepackage{booktabs}
  \usepackage{pdflscape}
  \newcommand{\blandscape}{\begin{landscape}}
  \newcommand{\elandscape}{\end{landscape}}
  \usepackage{longtable}
  \usepackage{array}
  \usepackage{ragged2e}
  \usepackage{etoolbox}
  \AtBeginEnvironment{longtable}{\scriptsize}
  \setlength{\LTpre}{6pt}\setlength{\LTpost}{10pt}
  \usepackage{titlesec}
  \usepackage{abstract}
  \newcommand{\babstract}{\begin{abstract}}
  \newcommand{\eabstract}{\end{abstract}}
  \renewcommand{\abstractnamefont}{\normalfont\bfseries}
  \renewcommand{\abstracttextfont}{\normalfont\small}
  \setlength{\absleftindent}{0pt}\setlength{\absrightindent}{0pt}
  \titleformat{\section}{\normalfont\large\bfseries}{\thesection}{0.6em}{}
  \setlength{\parskip}{0.5em}\setlength{\parindent}{0pt}
---

"""

WIDE_TABLE_HEADER = "| Experiment family |"


def main(src, dst):
    text = io.open(src, encoding="utf-8").read().replace("\r\n", "\n")
    lines = text.split("\n")

    title = lines[0].lstrip("# ").strip()
    start = next(i for i, l in enumerate(lines) if l.startswith("## Summary"))
    body = "\n".join(lines[start:])

    out = (HEADER % {"title": title}) + body

    # Summary becomes a real abstract, via macros so pandoc keeps parsing the markdown.
    out = out.replace("## Summary\n", "\\babstract\n\n", 1)
    stop = out.index("## How to read this report")
    out = out[:stop] + "\\eabstract\n\n" + out[stop:]

    # The thirteen-column table gets a landscape page, again via macros.
    lines = out.split("\n")
    first = next(i for i, l in enumerate(lines) if l.startswith(WIDE_TABLE_HEADER))
    last = first
    while last < len(lines) and lines[last].startswith("|"):
        last += 1
    lines.insert(last, "\n\\elandscape\n")
    lines.insert(first, "\n\\blandscape\n")

    io.open(dst, "w", encoding="utf-8").write("\n".join(lines))
    print("wrote %s" % dst)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
