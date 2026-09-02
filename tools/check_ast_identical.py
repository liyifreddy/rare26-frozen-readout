# -*- coding: utf-8 -*-
"""Check that two Python files differ only in comments, docstrings and message text.

The published `container/inference.py` has its comments and log messages translated
into English. Everything that determines the numbers must be untouched. This parses
both files, strips docstrings, replaces string constants with a placeholder, and
compares the syntax trees.

It does not cover a difference confined to string constants. Those are log and
exception text here and cannot change a score; the script prints how many differ so
the limit of the check is visible.

Usage:
    python tools/check_ast_identical.py ORIGINAL.py PUBLISHED.py
"""
import ast
import sys


def strip(tree):
    """Remove docstrings and normalize string constants."""
    strings = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:]
    for node in ast.walk(tree):
        # An f-string's literal segments are message text. Their number and position
        # change whenever the wording changes, which says nothing about behavior.
        # What must be preserved is which expressions are interpolated, and in what
        # order, so keep only the FormattedValue nodes.
        if isinstance(node, ast.JoinedStr):
            kept = []
            for v in node.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    strings.append(v.value)
                else:
                    kept.append(v)
            node.values = kept
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append(node.value)
            node.value = "<str>"
    return tree, strings


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    trees, strs = [], []
    for p in sys.argv[1:]:
        t, s = strip(ast.parse(open(p, encoding="utf-8").read()))
        trees.append(ast.dump(t))
        strs.append(s)

    same = trees[0] == trees[1]
    n_diff = sum(1 for a, b in zip(*strs) if a != b) + abs(len(strs[0]) - len(strs[1]))
    print("files:")
    for p in sys.argv[1:]:
        print("  %s" % p)
    print("structure identical after removing docstrings and string text: %s"
          % ("yes" if same else "NO"))
    print("string constants that differ (log and message text): %d of %d"
          % (n_diff, max(len(strs[0]), len(strs[1]))))
    if not same:
        print("\nThe syntax trees differ. The published file is NOT a comment-only "
              "translation of the original; investigate before publishing.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
