"""Sphinx configuration for Lium SDK documentation."""

import importlib.metadata
import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.abspath("..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

project = "Lium SDK"
author = "Lium"
copyright = f"{datetime.now():%Y}, {author}"

try:
    release = importlib.metadata.version("lium")
except importlib.metadata.PackageNotFoundError:
    release = "0.0.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
autodoc_typehints = "description"
autodoc_mock_imports = ["paramiko", "requests", "dotenv"]

templates_path = ["_templates"]
exclude_patterns: list[str] = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "style_external_links": False,
}
html_static_path = ["_static"]
