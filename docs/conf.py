# Configuration file for the Sphinx documentation builder.

project = "ckernel"
copyright = "2023, Adam Tuft"
author = "Adam Tuft"

release = "0.5.1"
version = "0.5"

extensions = [
    "sphinx.ext.duration",
    "sphinx.ext.doctest",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
intersphinx_disabled_domains = ["std"]

templates_path = ["_templates"]

# Options for HTML output

html_theme = "pydata_sphinx_theme"

html_title = f"c-kernel {version}"
