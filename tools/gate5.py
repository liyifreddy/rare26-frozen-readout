"""Gate 5: every prose paragraph of REPORT.md must appear in the rendered PDF."""
import io,re,sys
LIG={"ﬀ":"ff","ﬁ":"fi","ﬂ":"fl","ﬃ":"ffi","ﬄ":"ffl"}
BASE=str.maketrans({"’":"'","‘":"'","“":'"',"”":'"',"–":"-","—":"-","−":"-"," ":" "})
def norm(s,pdf=False):
    for a,b in LIG.items(): s=s.replace(a,b)
    if pdf:
        # pdftotext puts the page number at the end of each page. It usually sits on its
        # own line, but when a hyphenated word breaks across the page it is glued to the
        # word ("keep un8" for "unchanged"). Strip exactly the page's own number, per page,
        # rather than any trailing digits, so a paragraph that really ends in a number is
        # left alone.
        pages=s.split("\f")
        # (?<!\d) so a page that legitimately ends in a number is left alone:
        # without it a page ending "... in 1998" on page 8 becomes "... in 199".
        s="\n".join(re.sub(rf"(?<!\d){i+1}\s*$","",p.rstrip()) for i,p in enumerate(pages))
        s=re.sub(r"\n\s*\d{1,3}\s*\n","\n",s)
        s=re.sub(r"-\n\s*","",s)                # LaTeX hyphenation: drop hyphen + break
    else:
        s=re.sub(r"-\n\s*","-",s)               # markdown hard wrap: keep the real hyphen
        s=re.sub(r"-{2,}","-",s)                # LaTeX turns -- and --- into dashes
    s=re.sub(r"[`*_#]","",s); s=s.translate(BASE)
    s=re.sub(r"\s+"," ",s).strip()
    # Compared with whitespace and hyphens removed. Both differ between the two sides
    # for typesetting reasons alone: LaTeX breaks long URLs at hyphens and pdftotext
    # drops the hyphen at the break, and a word hyphenated across a page boundary comes
    # back as two pieces with the page number wedged between them. The cost, stated so
    # it is visible: a difference that is nothing but whitespace or a hyphen will not be
    # caught. Every other difference will.
    return re.sub(r"[\s-]+","",s)
md=io.open(sys.argv[1],encoding="utf-8").read().replace("\r\n","\n")
Pn=norm(io.open(sys.argv[2],encoding="utf-8").read(),True)
paras=[p for p in md.split("\n\n") if p.strip() and not p.strip().startswith(("|","#","```"))
       and len(p.split())>12]
miss=[norm(p) for p in paras if norm(p) not in Pn]
probe="A sentence deliberately absent from the rendered document."
extra=len([p for p in paras+[probe] if norm(p) not in Pn])
ok_self = extra==len(miss)+1
print(f"paragraphs {len(paras)}   missing {len(miss)}   self-test {'OK' if ok_self else 'GATE BROKEN'}")
for m in miss: print("   MISSING:", m[:110])
sys.exit(0 if (not miss and ok_self) else 1)
