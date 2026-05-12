Releasing to PyPI
=================

Maintainer-facing notes for cutting a release. Contributors do not
need to read this section.

Releases publish to PyPI via the
`Trusted Publishers / OIDC <https://docs.pypi.org/trusted-publishers/>`__
workflow (:file:`.github/workflows/publish_to_pypi.yml`). No
long-lived ``PYPI_API_TOKEN`` secret is stored in the repository.

One-time setup (release blocker for the first publish)
------------------------------------------------------

The OIDC workflow fails with ``invalid-publisher`` until a trusted
publisher is configured on the PyPI side. Because the project has
never been uploaded, the per-project settings page does not exist
yet — use the **pending publisher** form instead, which lets PyPI
pre-authorize a name and convert it to a real publisher on the first
successful upload.

1. Determine the GitHub owner / repo from the remote URL:

   .. code-block:: bash

      git remote get-url origin
      # → e.g. https://github.com/<OWNER>/<REPO>.git

   Use the exact ``<OWNER>`` / ``<REPO>`` strings from that output,
   case-sensitive, in the steps below.

2. On https://pypi.org/manage/account/publishing/, scroll to
   "Add a new pending publisher" → "GitHub":

   * PyPI Project Name: ``rms-picmaker``
   * Owner: ``<OWNER>`` (from step 1)
   * Repository name: ``<REPO>`` (from step 1)
   * Workflow filename: ``publish_to_pypi.yml``
   * Environment name: ``pypi``

   The project name must be available — PyPI rejects the form if
   someone has reserved it.

3. Repeat on https://test.pypi.org/manage/account/publishing/ with
   workflow filename ``publish_to_test_pypi.yml`` and environment
   name ``testpypi``. TestPyPI is a separate registry with its own
   name reservations and its own pending publisher list.

4. In the GitHub repo, configure Environments → New environment
   ``pypi`` (and ``testpypi``). The publish jobs run inside these
   environments so PyPI can verify the OIDC claim.

5. After the first successful upload, the pending publisher promotes
   to a regular trusted publisher and the per-project settings page
   (https://pypi.org/manage/project/rms-picmaker/settings/publishing/)
   becomes the place to manage it going forward.

Cutting a release
-----------------

1. Ensure CI is green on the branch you intend to tag.

2. Tag the commit and push the tag:

   .. code-block:: bash

      git tag v0.1.0
      git push --tags

   :file:`publish_to_pypi.yml` fires on ``release: published``, so
   creating a GitHub Release pointing at the tag triggers the
   upload. To dry-run against TestPyPI first, trigger
   :file:`publish_to_test_pypi.yml` manually from the Actions tab.

3. After the upload completes, verify the release at
   https://pypi.org/project/rms-picmaker/.
