// MathJax 3 configuration for the Energytools docs site.
// Loaded via mkdocs.yml `extra_javascript` together with the MathJax CDN bundle.
// pymdownx.arithmatex (generic mode) converts `$...$` / `$$...$$` in the Markdown
// sources into `\(...\)` / `\[...\]` spans; MathJax then typesets those spans.
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  }
};
