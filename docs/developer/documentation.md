# Documentation

The site is built with MkDocs and the Material theme from the Markdown files under `docs/`, as
configured by `mkdocs.yml` at the repository root. Every page is also meant to read correctly on
GitHub, so the conventions below are the ones both renderers agree on. The site is published at
<https://danielepanozzo.github.io/kairn/> from every push to `main`, by the workflow that builds
and checks it (`checks.yml`).

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

The pages under `docs/reference/`, except `reading.md` and the pages that `PAGES` of
`docs/tools/reference_operations.py` lists (`rational.md`, for operations that call no kernel), are
generated and committed, like the generated C++, and the Reference part of `nav` in `mkdocs.yml` is
generated between the lines `# BEGIN reference` and `# END reference`, the pages of `PAGES` in it:

```sh
python3 docs/tools/reference.py          # rewrite them
python3 docs/tools/reference.py --check  # fail if one differs from what would be written
python3 docs/tools/test_reference.py     # the tests of the script and of its table
```

The script reads `gen/claims.json`, the kernel descriptions under `gen/kernels/`,
`include/kairn/gen/bounds.hpp`, `proofs/gen/Statements.v`, the axiom audit's allow-list and files
(below), and the stored brute-force summaries of the latest milestone under `results/`, and prints
every number, status and formula of a page from them. Rerun it after any of these changes;
`--check` and the tests run in CI (the workflow `checks.yml`) and in ctest: `docs.reference.check`
in the quick tier, and `full.tools.docs.reference.test` in the full tier.

The one input written by hand is `docs/tools/reference_operations.py`: for each kernel its page's
title and group, and the C++ forms that reach it, with their operand types. A new kernel needs an
entry there (the script refuses to run without one), and the test fails when a public operation
whose header comment names a kernel is not among that kernel's forms.

The script knows the claim kinds, fields and requirements of `docs/developer/architecture.md`
("Claims", "Claims of the second wave", "Claims of the non-finite layer"), each in the domain where
that page gives it a meaning, and nothing else: on a kind, a requirement, a field, a condition, a
lead or a status it has no template for, it stops and names it, so that someone writes the
template before the pages change. Whether a kernel has a statement on finite operands is what the
claims say with `ieee_only`, and nothing else. A kernel of the extended domain without
`ieee_only` keeps its statement on finite operands (`canonical` and `ball` read as their finite
cases, `represents` left out) and gets a section "Infinite and NaN operands"; a kernel with
`"ieee_only": true` (a full kernel, a constructor) has the statement in the IEEE model only (F1 to
F5, B1 to B4, or that of the constructor), printed with the kernel's own names, its core's bound
and its `finite_when` conditions. Every status comes from `status` and `ieee_status`, never from
anything else. `python3 docs/tools/reference.py --claims PATH` renders the pages from another
claims file, in memory, to try claims that are not committed.

A kernel whose description says `entry: yes` and that has no form in the table is one the public
headers may call but do not call yet, and its page and the index say so. When a header starts to
call it, the test fails until its forms are in the table.

Each page names the theorems it calls proved, the audit file that prints their assumptions
(`Print Assumptions`, in `proofs/gen/Audit.v`, `proofs/gen/IeeeAudit.v` or
`proofs/audit/HandAudit.v`), and the axioms of `proofs/audit/allowed_axioms.txt`; the script fails
on a proved theorem that no audit file names. Which of the allowed axioms a theorem depends on is
known only by running Rocq, so no page lists them per theorem: the page points to the artifact
`proof-audit` of the workflow `proofs.yml`, which keeps what the audit printed.

## The C++ API reference

The pages under `api/` of the site are Doxygen's HTML, generated from the comments of the public
headers, `include/kairn/*.hpp`. The generated headers of `include/kairn/gen/`, the namespaces
`kairn::detail` and `kairn::gen` and the macros named `KAIRN_DETAIL_*` are left out: they are not
part of the interface. The configuration is `docs/Doxyfile`, and the first page is
`docs/api/mainpage.md`. Doxygen writes into `site/api/`, over the page that MkDocs makes there
from `docs/api/index.md`, so it runs after MkDocs, from the repository root:

```sh
.venv/bin/mkdocs build --strict
doxygen docs/Doxyfile            # writes site/api/; any warning fails it
open site/api/index.html         # or xdg-open on Linux, start on Windows
```

`mkdocs serve` builds the site again without Doxygen, so in its preview `api/` is the page of
`docs/api/index.md`, which says where the reference comes from.

The configuration is checked with Doxygen 1.18.0, the release the CI installs (the workflow
`checks.yml` downloads it and checks its SHA-256). Ubuntu 24.04's package, Doxygen 1.9.8, gave the
same result, with no warning, on the headers of this version. The CI keeps the site with the API
reference in it as the artifact `site`.

Every public entity has a comment, written `///` before its declaration, and a warning fails the
build: an entity without a comment, or a comment that Doxygen cannot read. Two rules make that
work:

- Each public header begins with a `/// @file` comment. Doxygen lists the macros and functions of
  a file, and the members of a namespace, only when the file or the namespace has a comment of its
  own; the namespace `kairn` has one, before `namespace kairn` in `config.hpp`.
- In a comment, write code in backticks: outside them, `#if` is read as a link to an entity named
  `if`, and Doxygen warns that it cannot find it.
