# Deploy Skipper 🚀

**Smart, zero-dependency deployment gating for your CI/CD pipeline.**
Stop deploying when nothing meaningful changed — save time, reduce errors, and speed up your workflow.

---

## Why Deploy Skipper?

Imagine running a deployment every time **any file changes**, even trivial docs or images. Wasted time, wasted resources, and unnecessary production churn.

`Deploy Skipper` intelligently decides **whether a deployment is necessary** by checking your changed files against **blacklist & whitelist rules**, giving you full control over what triggers your CI/CD.

---

## Features

* ✅ **Blacklist + Whitelist Support**
  Ignore irrelevant files (`*.md`, `images/*`) while explicitly allowing critical ones (`config/settings.yaml`).

* ✅ **Git-Aware**
  Automatically diffs against commits, branches, or the most recent tag.

* ✅ **Recursive & Flexible Globs**
  Supports `*`, `**`, and directory patterns (`dir/*`) out-of-the-box.

* ✅ **Zero Dependencies**
  Pure Python 3 — no external libraries required.

* ✅ **Verbose & JSON Modes**
  See exactly which files matched patterns and whether they will trigger a deploy.

* ✅ **CI/CD Friendly**
  Exit codes map perfectly to CI logic:

  * `0` → deploy (relevant changes found)
  * `1` → skip (only ignored changes)
  * `2` → error/misconfiguration

---

## Installation

**Option 1: Standalone script**

```bash
curl -O https://raw.githubusercontent.com/philsupertramp/deploy_skipper/main/deploy_skipper.py
chmod +x deploy_skipper.py
./deploy_skipper.py
```

Optionally, you can also build the executable yourself
```bash
curl -O https://raw.githubusercontent.com/philsupertramp/deploy_skipper/main/deploy_skipper.py
python -m venv
. venv/bin/activate
pip install pyinstaller
pyinstaller --onefile deploy_skipper.py

# this builds into ./dist
./dist/deploy_skipper --help
```

**Option 2: Install via pip (recommended)**

```bash
pip install deploy_skipper
deploy_skipper
```

> Once installed, the `deploy_skipper` command is available.

---

## Usage

```bash
# Diff against previous commit
deploy_skipper

# Diff against the most recent tag
deploy_skipper --tag

# Diff against a specific commit
deploy_skipper --ref 3f4e2a1

# Use a custom ignore file
deploy_skipper --ignore-file .mydeployignore

# See verbose output of what triggered the deploy
deploy_skipper --verbose
```

---

## `.deployignore` Format

* **Blacklist patterns** (ignored files) – default: lines without `!`
* **Whitelist patterns** (un-ignore files) – prefix lines with `!`

```text
# Ignore all markdown files
*.md

# Ignore images
images/*

# Ignore everything in build/ but allow a critical config
build/*
!build/config.json

# Ignore all JS but allow main.js
src/**/*.js
!src/main.js
```

> Whitelist always wins. Even if a file matches a blacklist pattern, if it’s in the whitelist, it will trigger a deploy.

---

## Examples

### Skip deployment for docs-only changes

```bash
# .deployignore
*.md
docs/*

# Git changes
git diff HEAD~1 --name-only
README.md
docs/setup.md
```

```bash
deploy_skipper --verbose
# Output:
# README.md: matched blacklist pattern '*.md' -> IGNORED
# docs/setup.md: matched blacklist pattern 'docs/*' -> IGNORED
# All changes are ignored by blacklist/whitelist rules; skipping deployment.
```

✅ Result: **CI/CD skips deploy**, saving time.

---

### Trigger deployment for config changes

```bash
# .deployignore
*.md
!config/settings.yaml

# Git changes
git diff HEAD~1 --name-only
README.md
config/settings.yaml
```

```bash
deploy_skipper --verbose
# Output:
# README.md: matched blacklist pattern '*.md' -> IGNORED
# config/settings.yaml: matched whitelist pattern 'config/settings.yaml' -> RELEVANT
# Relevant changes detected, proceeding with deployment:
#   config/settings.yaml
```

✅ Result: **CI/CD triggers deploy**, as intended.

---

## Integration Tips

* **GitHub Actions / GitLab CI / Jenkins**
  Use the exit code directly:

  ```yaml
  - name: Check if deployment is needed
    run: deploy_skipper
  ```
* **Dry run** for debugging (verbose output shows exactly what is happening)
* Combine with caching & notifications for maximum CI efficiency

---

## Why You’ll Love It

* Save hours of unnecessary deployments
* Reduce deployment-related errors
* Full control over what changes actually matter
* Transparent & easy-to-read logs
* Works on any platform with Python 3

---

## Contribute

We welcome PRs, suggestions, or improvements!

* Add support for **JSON output** for machine-readable CI logs
* Improve **pattern matching rules** for edge cases
* Add **integration templates** for popular CI/CD systems

---

## License

MIT License – use freely in personal or commercial projects.
