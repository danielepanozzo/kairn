# Documentation

The site is built with MkDocs and the Material theme from the Markdown files under `docs/`, as
configured by `mkdocs.yml` at the repository root. Every page is also meant to read correctly on
GitHub, so the conventions below are the ones both renderers agree on. The site is not published
yet.

## Building the site

From the repository root:

```sh
python3 -m venv .venv                            # once; .venv/ is ignored by git
.venv/bin/pip install -r docs/requirements.txt   # the pinned versions
.venv/bin/mkdocs serve                           # http://127.0.0.1:8000, rebuilt on every change
.venv/bin/mkdocs build --strict                  # writes site/, also ignored by git
python3 docs/tools/check_links.py
```

On Windows the programs are under `.venv\Scripts\` instead of `.venv/bin/`.

Run the last two after changing a page:

- `mkdocs build --strict` turns every warning into an error: a link to a page or an anchor that
  does not exist, a page under `docs/` that is not in the navigation, an absolute link, an
  included file that does not exist.
- `docs/tools/check_links.py` needs only Python. It checks that every relative link and anchor in
  the pages and in `README.md` also resolves on GitHub, and that a linked heading has the same
  anchor on GitHub and on the site.

## Pages and navigation

Every page is listed under `nav` in `mkdocs.yml`; a strict build fails on a page that is not. The
sections follow the outline in the [Plan](design/phase0/plan.md#documentation-outline), and a
section is added with its first page that has something to say, not as an empty stub.

## Links and anchors

- Link to another page by the relative path of its `.md` file, with an anchor if needed:
  `[Numbers](design/phase0/numbers.md#the-normalization-invariant)`. GitHub and MkDocs both
  resolve these.
- Link to a file outside `docs/` (code, experiments) by its URL on GitHub, since the site contains
  only `docs/`.
- A heading's anchor is its text in lower case, without punctuation, with spaces replaced by
  hyphens. Where punctuation stands between two spaces (`k = 1`, `a + b`, a dash), GitHub keeps
  two hyphens and MkDocs one, so the anchors differ: do not link to such a heading, or give the
  place an explicit anchor, `<a id="name"></a>`, which both keep (the
  [References](design/phase0/references.md) page does this).

## Mathematics

- Inline mathematics is `$...$`, displayed mathematics `$$...$$` as a paragraph of its own. GitHub
  renders both; on the site `pymdownx.arithmatex` marks them and MathJax typesets them. The other
  delimiters, `\(...\)` and `\[...\]`, are not recognized on the site, because GitHub does not
  render them.
- No space after the opening `$` or before the closing one.
- In a table, write $\lvert x\rvert$ as `\lvert x\rvert`, not `|x|`: a `|` ends the cell.

## Angle brackets and code

Write names such as `Expansion<T, k>` in backticks. Outside a code span, MkDocs takes `<T, k>` for
an HTML tag and the page loses it, while GitHub shows it.

`--8<-- "path"` inside a fenced code block includes a file, with the path relative to the
repository root (`pymdownx.snippets`); a missing file fails the build. [Getting
started](../getting-started/index.md) includes the consumer checks' `CMakeLists.txt` files this
way, so what the page shows is what ctest builds. GitHub shows the include line itself.

## Examples

Every fragment of C++ on a page is a section of a complete program under `docs/examples/cpp/`,
marked in the program with `// --8<-- [start:NAME]` and `// --8<-- [end:NAME]` and included as
`--8<-- "docs/examples/cpp/PROGRAM.cpp:NAME"`. ctest builds every example with warnings as errors
and runs it (`api.example.*`, registered in `tests/api/CMakeLists.txt`), and the program checks
its own results and exits with a status other than 0 when one is wrong. When a page shows what a
program prints, the output is a file next to it, `PROGRAM.txt`, included the same way, and the test
compares the program's output with it (`tests/api/example_output.cmake`), so the output must be
the same on every platform. [Accurate sums](../tutorials/accurate-sums.md) is built this way, once
with the build's flags and once per contraction setting of the compiler. After changing such a
program, write its new output into the `.txt` file and check the page that includes it.

## Reference pages

The pages under `docs/reference/`, except `reading.md`, are generated and committed, like the
generated C++, and the Reference part of `nav` in `mkdocs.yml` is generated between the lines
`# BEGIN reference` and `# END reference`:

```sh
python3 docs/tools/reference.py          # rewrite them
python3 docs/tools/reference.py --check  # fail if one differs from what would be written
python3 docs/tools/test_reference.py     # the tests of the script and of its table
```

The script reads `gen/claims.json`, the kernel descriptions under `gen/kernels/`,
`include/kairn/gen/bounds.hpp`, `proofs/gen/Statements.v` and the stored brute-force summaries of
the latest milestone under `results/`, and prints every number, status and formula of a page from
them. Rerun it after any of these changes; `--check` runs in CI (the workflow `checks.yml`) and in
ctest (`docs.reference.check`, `docs.reference.test`).

The one input written by hand is `docs/tools/reference_operations.py`: for each kernel its page's
title and group, and the C++ forms that reach it, with their operand types. A new kernel needs an
entry there (the script refuses to run without one), and the test fails when a public operation
whose header comment names a kernel is not among that kernel's forms.

The script knows the claim kinds and requirements of `docs/developer/architecture.md`
("Claims", "Claims of the second wave") and nothing else: on a kind, a requirement, a field or a
status it has no template for, it stops and names it, so that someone writes the template before
the pages change. Kernels with `"domain": "extended"` are handled by one switch at the top of the
script, `EXTENDED_DOMAIN`: `"fail"` (the committed value) stops on them, `"skip"` leaves them out
and lists them on the index as not rendered yet.
