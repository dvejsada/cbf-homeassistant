# Releasing a new version

Users install and update the integration through the Home Assistant **Marketplace** (HACS). It offers each published **GitHub release** as a version. When a new release is out, users see an update in **Settings → Updates**.

## Steps

1. Make sure `main` contains everything you want to ship, and that the tests pass:

   ```bash
   python -m pytest -q
   ```

2. Pick the new version using [semantic versioning](https://semver.org):
   - **patch** (`0.1.1`) for fixes
   - **minor** (`0.2.0`) for new features
   - **major** (`1.0.0`) for breaking changes, e.g. renamed entities

3. Set it in `manifest.json`, then commit and push:

   ```bash
   python script/bump_version.py 0.2.0
   ```

   ```bash
   git commit -am "Release v0.2.0"
   ```

   ```bash
   git push
   ```

4. Tag the commit and push the tag:

   ```bash
   git tag v0.2.0
   ```

   ```bash
   git push origin v0.2.0
   ```

   The **Release** workflow (`.github/workflows/release.yml`) then:
   - checks that the tag matches the version in `manifest.json`
   - publishes a GitHub release with notes generated from the merged pull requests

   A tag containing a hyphen, such as `v0.2.0-beta.1`, is published as a **pre-release**. The Marketplace shows pre-releases only to users who turned on beta versions for this repository.

## If GitHub Actions is not available

Create the release by hand. On GitHub, open **Releases → Draft a new release**, choose the tag (for example `v0.2.0`), click **Generate release notes**, and then **Publish release**. The tag must match the `version` in `manifest.json`.

## Checking it in Home Assistant

The Marketplace checks custom repositories for new releases only occasionally, roughly every 48 hours. To see a new release immediately, open the repository in the Marketplace and choose **⋮ → Refresh information**.
