# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

import tomllib

sys.path.insert(0, os.path.abspath("../src"))


# Read version from pyproject.toml
def get_version():
    try:
        with open("../pyproject.toml", "rb") as f:
            data = tomllib.load(f)
            return data["project"]["version"]
    except Exception:
        return "0.1.2"  # fallback


project = "fapilog"
copyright = "2024, Chris Haste"
author = "Chris Haste"
release = get_version()
version = get_version()

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "myst_parser",  # For markdown support
]

templates_path = ["_templates"]
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "*.md",  # Exclude all markdown files to avoid conflicts
    "stories/*",  # Exclude story files
    "REVIEW.md",
    "api-reference.md",
    "user-guide.md",
    "config.md",
    "container-architecture.md",
    "error-handling-implementation-summary.md",
    "story-13-refactored-summary.md",
    "architecture-improvements-summary.md",
    "epics.md",
    "documentation-structure.md",
    "prd-phase-1-mvp.md",
    "sprint-planning-weeks-1-4.md",
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# -- Extension configuration -------------------------------------------------

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "fastapi": ("https://fastapi.tiangolo.com", None),
    "structlog": ("https://www.structlog.org/en/stable/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

# MyST parser settings for markdown support
myst_enable_extensions = [
    "deflist",
    "tasklist",
    "colon_fence",
    "fieldlist",
    "attrs_inline",
]

# TODO extension
todo_include_todos = True

# HTML theme options
html_theme_options = {
    "canonical_url": "",
    "analytics_id": "",
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": False,
    "vcs_pageview_mode": "",
    "style_nav_header_background": "#2980B9",
    # TOC options
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 4,
    "includehidden": True,
    "titles_only": False,
}

# Custom sidebar
html_sidebars = {
    "**": [
        "about.html",
        "navigation.html",
        "relations.html",
        "searchbox.html",
        "donate.html",
    ]
}

# Additional HTML context
html_context = {
    "display_github": True,
    "github_user": "chris-haste",
    "github_repo": "fastapi-logger",
    "github_version": "main",
    "conf_py_path": "/docs/",
}

# Master document (index page)
master_doc = "index"

# Source file extensions
source_suffix = {
    ".rst": None,
}
