// MathJax 3 for pymdownx.arithmatex in generic mode (mkdocs.yml): arithmatex turns $...$ into
// \(...\) and $$...$$ into \[...\] inside elements of class "arithmatex", and MathJax typesets
// those elements only.
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true,
  },
  options: { ignoreHtmlClass: ".*|", processHtmlClass: "arithmatex" },
};

// Material emits document$ for every page it shows (also when it swaps pages without a reload).
document$.subscribe(() => {
  MathJax.startup.output.clearCache();
  MathJax.typesetClear();
  MathJax.texReset();
  MathJax.typesetPromise();
});
