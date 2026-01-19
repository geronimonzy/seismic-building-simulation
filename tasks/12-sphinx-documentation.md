# Task 12: Sphinx Documentation

## Priority: HIGH
## Estimated Effort: 3-5 days

## Problem Statement

The current project:
- Has minimal user documentation
- No API reference with examples
- No getting started guide
- No hosted documentation site

## Implementation Plan

### 1. Set up Sphinx structure
Create `docs/` directory:

```
docs/
├── conf.py
├── index.rst
├── Makefile
├── requirements.txt
├── getting_started/
│   ├── index.rst
│   ├── installation.rst
│   ├── quickstart.rst
│   └── first_analysis.rst
├── user_guide/
│   ├── index.rst
│   ├── building_models.rst
│   ├── ground_motion.rst
│   ├── time_history.rst
│   ├── calibration.rst
│   └── uncertainty.rst
├── api/
│   ├── index.rst
│   ├── building.rst
│   ├── ground_motion.rst
│   ├── analysis.rst
│   ├── calibration.rst
│   └── uncertainty.rst
└── advanced/
    ├── index.rst
    ├── custom_models.rst
    ├── performance.rst
    └── real_data.rst
```

### 2. Configure Sphinx
Create `docs/conf.py`:

```python
# Configuration file for Sphinx documentation builder.

import os
import sys
sys.path.insert(0, os.path.abspath('../src'))

project = 'Seismic Digital Twin'
copyright = '2024'
author = 'Seismic Twin Team'
release = '0.1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx.ext.mathjax',
    'myst_parser',
    'sphinx_copybutton',
    'nbsphinx',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# HTML theme
html_theme = 'furo'
html_static_path = ['_static']
html_title = "Seismic Digital Twin"

# Napoleon settings (for Google/NumPy docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}
autosummary_generate = True

# Intersphinx
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
}

# MyST parser for Markdown
myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# nbsphinx for Jupyter notebooks
nbsphinx_execute = 'never'  # Don't execute notebooks during build
```

### 3. Create main index
Create `docs/index.rst`:

```rst
Seismic Digital Twin
====================

A Python package for seismic building response simulation with sensor-based
model calibration and uncertainty quantification.

.. image:: https://img.shields.io/badge/python-3.9+-blue.svg
   :target: https://www.python.org/downloads/

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started/installation
   getting_started/quickstart
   getting_started/first_analysis

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user_guide/building_models
   user_guide/ground_motion
   user_guide/time_history
   user_guide/calibration
   user_guide/uncertainty

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/building
   api/ground_motion
   api/analysis
   api/calibration
   api/uncertainty

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   advanced/custom_models
   advanced/performance
   advanced/real_data

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

### 4. Create installation guide
Create `docs/getting_started/installation.rst`:

```rst
Installation
============

Requirements
------------

- Python 3.9 or higher
- NumPy, SciPy, Matplotlib

Basic Installation
------------------

Install from PyPI (when available):

.. code-block:: bash

   pip install seismic-twin

Or install from source:

.. code-block:: bash

   git clone https://github.com/your-repo/seismic-building-simulation.git
   cd seismic-building-simulation
   pip install -e .

Development Installation
------------------------

For development with all optional dependencies:

.. code-block:: bash

   pip install -e ".[dev]"

This includes:

- pytest for testing
- Sphinx for documentation
- ruff for linting

Optional Dependencies
---------------------

For performance optimization:

.. code-block:: bash

   pip install numba  # JIT compilation (~50x speedup)

For GPU acceleration:

.. code-block:: bash

   pip install cupy-cuda11x  # NVIDIA CUDA support

For real data integration:

.. code-block:: bash

   pip install obspy  # FDSN seismic data access
```

### 5. Create quickstart guide
Create `docs/getting_started/quickstart.rst`:

```rst
Quickstart
==========

This guide walks through a minimal example.

Create a Building Model
-----------------------

.. code-block:: python

   from seismic_twin.building import MDOFShearBuilding

   building = MDOFShearBuilding(
       masses=[100e3, 100e3, 100e3],      # kg per floor
       stiffnesses=[50e6, 50e6, 50e6],    # N/m per story
       damping_ratio=0.05,                 # 5% critical
       story_heights=[3.5, 3.5, 3.0],     # meters
   )

Generate Ground Motion
----------------------

.. code-block:: python

   from seismic_twin.ground_motion import generate_synthetic_ground_motion

   time, ground_acc = generate_synthetic_ground_motion(
       duration=30.0,    # seconds
       dt=0.01,          # time step
       target_pga=0.3,   # peak ground acceleration in g
   )

Run Time History Analysis
-------------------------

.. code-block:: python

   from seismic_twin.analysis import newmark_beta

   result = newmark_beta(
       building.M, building.C, building.K,
       ground_acc, dt=0.01
   )

   print(f"Max roof displacement: {result.displacement[:, -1].max():.3f} m")

Visualize Results
-----------------

.. code-block:: python

   import matplotlib.pyplot as plt

   plt.figure(figsize=(10, 4))
   plt.plot(result.time, result.displacement[:, -1])
   plt.xlabel("Time (s)")
   plt.ylabel("Roof Displacement (m)")
   plt.title("Building Response to Earthquake")
   plt.show()
```

### 6. Create API reference pages
Create `docs/api/building.rst`:

```rst
Building Models
===============

.. automodule:: seismic_twin.building
   :members:
   :undoc-members:
   :show-inheritance:

MDOFShearBuilding
-----------------

.. autoclass:: seismic_twin.building.MDOFShearBuilding
   :members:
   :special-members: __init__

   Example
   ~~~~~~~

   .. code-block:: python

      from seismic_twin.building import MDOFShearBuilding

      # Create a 5-story building
      building = MDOFShearBuilding(
          masses=[100e3] * 5,
          stiffnesses=[50e6] * 5,
          damping_ratio=0.05,
          story_heights=[3.5] * 5,
      )

      # Access system matrices
      print(f"Mass matrix shape: {building.M.shape}")
      print(f"Natural frequencies: {building.natural_frequencies} Hz")
```

### 7. Add documentation build to CI
Add to `.github/workflows/docs.yml`:

```yaml
name: Documentation

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -e ".[dev]"
        pip install -r docs/requirements.txt

    - name: Build documentation
      run: |
        cd docs
        make html

    - name: Upload artifact
      uses: actions/upload-pages-artifact@v2
      with:
        path: docs/_build/html

  deploy:
    if: github.ref == 'refs/heads/main'
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
    - name: Deploy to GitHub Pages
      id: deployment
      uses: actions/deploy-pages@v3
```

### 8. Create docs requirements
Create `docs/requirements.txt`:

```
sphinx>=7.0
furo
myst-parser
sphinx-copybutton
nbsphinx
ipython
```

## Files to Create

| File | Action |
|------|--------|
| `docs/conf.py` | Create |
| `docs/index.rst` | Create |
| `docs/Makefile` | Create |
| `docs/requirements.txt` | Create |
| `docs/getting_started/*.rst` | Create |
| `docs/user_guide/*.rst` | Create |
| `docs/api/*.rst` | Create |
| `docs/advanced/*.rst` | Create |
| `.github/workflows/docs.yml` | Create |

## Success Criteria

- [ ] Documentation builds without errors
- [ ] API reference auto-generated from docstrings
- [ ] Getting started guide complete
- [ ] User guide covers all major features
- [ ] Docs deployed to GitHub Pages
- [ ] All code examples work
