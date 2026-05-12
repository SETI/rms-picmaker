# Contributing to rms-picmaker

Thank you for your interest in contributing to rms-picmaker! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

We expect all contributors to follow our Code of Conduct, which ensures a welcoming and inclusive environment for everyone.
See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/your-username/rms-picmaker.git
   cd rms-picmaker
   ```

3. Create a virtual environment and install the package with dev dependencies:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e ".[dev]"
   ```

## Development Workflow

1. Create a new branch for your feature or bugfix:

   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b bugfix/issue-number
   ```

2. Make your changes, following our coding standards
3. Write or update tests as necessary
4. Run the tests and lint to ensure they pass:

   ```bash
   scripts/run-all-checks.sh
   ```

5. Commit your changes with a descriptive message:

   ```bash
   git commit -m "Add feature: description of your changes"
   ```

6. Push your branch to your fork:

   ```bash
   git push origin feature/your-feature-name
   ```

7. Open a Pull Request on GitHub

## Coding Standards

We follow these standards for all code contributions:

* **Python Style**: Follow PEP 8
* **Type Hints**: Use type hints for all function parameters and return values
* **Docstrings**: Document all classes and methods with docstrings following the Google style
* **Testing**: Include unit tests for new functionality
* **Compatibility**: Ensure compatibility with Python 3.11+

Example of a well-formatted function:

```python
def calculate_offset(image: NDArrayFloatType, model: NDArrayFloatType) -> tuple[float, float]:
    """Calculate the offset between an image and a model.

    Parameters:
        image: The observed image as a NumPy array
        model: The theoretical model as a NumPy array

    Returns:
        A tuple containing the (u, v) offset in pixels
    """
    # Implementation here
    return u_offset, v_offset
```

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if necessary
3. Make sure your code is properly formatted and passes both ruff and mypy
4. Request a review from a maintainer
5. Address any feedback from reviewers

The maintainers will merge your PR once it meets all requirements.

## Testing

We use pytest for testing. To run the tests:

```bash
pytest
```

For more verbose output:

```bash
pytest -v
```

To run a specific test file:

```bash
pytest tests/test_specific_file.py
```

## Documentation

We use Sphinx for documentation. To build the docs:

```bash
cd docs
make html
```

The generated documentation will be in `docs/_build/html`.

When adding new features, please update the relevant documentation:

* Update docstrings for new functions and classes
* Add examples if appropriate
* Update the user guide or developer guide if necessary

## Releasing to PyPI

Releases publish to PyPI via the
[Trusted Publishers / OIDC](https://docs.pypi.org/trusted-publishers/) workflow
(`.github/workflows/publish_to_pypi.yml`). No long-lived `PYPI_API_TOKEN` secret
is stored in the repository.

**Pre-merge manual step (release blocker).** Until the trusted publisher is
configured on the PyPI side, the workflow fails on first run with
`invalid-publisher`. Complete the following one-time setup before tagging the
first release:

1. Determine the GitHub owner / repo from the remote URL:

   ```bash
   git remote get-url origin
   # → e.g. https://github.com/<OWNER>/<REPO>.git
   ```

   Use the exact `<OWNER>` / `<REPO>` strings from that output, case-sensitive,
   in the steps below.

2. On <https://pypi.org/manage/project/rms-picmaker/settings/publishing/>,
   click "Add a new publisher" → "GitHub":

   * Owner: `<OWNER>` (from step 1)
   * Repository name: `<REPO>` (from step 1)
   * Workflow filename: `publish_to_pypi.yml`
   * Environment name: `pypi`

3. Repeat on
   <https://test.pypi.org/manage/project/rms-picmaker/settings/publishing/>
   with workflow filename `publish_to_test_pypi.yml` and environment name
   `testpypi`.

4. In the GitHub repo, configure Environments → New environment `pypi` (and
   `testpypi`). The publish jobs run inside these environments so PyPI can
   verify the OIDC claim.

5. Once configured, tag a release:

   ```bash
   git tag v0.1.0
   git push --tags
   ```

   The `publish_to_pypi.yml` workflow fires on release-published and uploads
   via OIDC. To publish to TestPyPI, trigger `publish_to_test_pypi.yml`
   manually from the Actions tab.

## Reporting Issues

If you find a bug or have a suggestion for improvement:

1. Check if the issue already exists in the GitHub issue tracker
2. If not, create a new issue with:
   * A clear, descriptive title
   * A detailed description of the issue
   * Steps to reproduce (for bugs)
   * Your environment information (Python version, OS, etc.)
   * Any relevant logs or screenshots

Thank you for contributing to rms-picmaker!
