#!/usr/bin/env python3
"""check_links.py [DIR]: every relative Markdown link under DIR (default: docs) points at an
existing file and, when it has a fragment, at a heading or an explicit <a id> of that file.

Heading anchors are computed the way GitHub does, and the script also fails when MkDocs' slug of
a linked heading would differ (headings with '=', '<', or a hyphen next to a space), so that a
page reads the same in both. `mkdocs build --strict` will replace this once the site exists."""
import os, re, sys
root = sys.argv[1] if len(sys.argv) > 1 else "docs"
def github_slug(h):
    h = re.sub(r"`|\*|\$", "", h.strip().lower())
    return re.sub(r" ", "-", re.sub(r"[^\w\- ]", "", h))
def mkdocs_slug(h):
    h = re.sub(r"`|\*|\$", "", h.strip().lower())
    return re.sub(r"[-\s]+", "-", re.sub(r"[^\w\s-]", "", h)).strip("-")
anchors, portable, errors = {}, {}, []
files = [os.path.join(d, f) for d, _, fs in os.walk(root) for f in fs if f.endswith(".md")]
for f in files:
    text = open(f).read()
    text_nocode = re.sub(r"```.*?```", "", text, flags=re.S)
    a, p = set(re.findall(r'<a id="([^"]+)"', text)), {}
    for h in re.findall(r"^#{1,6}\s+(.*)$", text_nocode, flags=re.M):
        a.add(github_slug(h)); p[github_slug(h)] = github_slug(h) == mkdocs_slug(h)
    anchors[os.path.normpath(f)], portable[os.path.normpath(f)] = a, p
for f in files:
    text = re.sub(r"```.*?```", "", open(f).read(), flags=re.S)
    for target in re.findall(r"\]\(([^)\s]+)\)", text):
        if re.match(r"[a-z]+://|mailto:", target):
            continue
        path, _, frag = target.partition("#")
        dest = os.path.normpath(os.path.join(os.path.dirname(f), path)) if path else os.path.normpath(f)
        if not os.path.exists(dest):
            errors.append(f"{f}: missing file {target}")
        elif frag and dest.endswith(".md"):
            if frag not in anchors.get(dest, ()):
                errors.append(f"{f}: no anchor #{frag} in {dest}")
            elif not portable[dest].get(frag, True):
                errors.append(f"{f}: anchor #{frag} in {dest} differs between GitHub and MkDocs")
print("\n".join(errors) if errors else f"{len(files)} files: all relative links and anchors resolve")
sys.exit(1 if errors else 0)
