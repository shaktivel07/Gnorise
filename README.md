# Gnorise 🧠

**Understand, clean, and secure your dependencies — before they break your project.**

[![CI/CD Ready](https://img.shields.io/badge/CI%2FCD-Ready-green.svg)](#ci-integration)
[![Tree-sitter Powered](https://img.shields.io/badge/Engine-Tree--sitter-blue.svg)](#how-it-works)

Gnorise is a production-ready developer tool that tracks, explains, and audits project dependencies with real usage insight. It goes beyond simple listing by analyzing your code's Abstract Syntax Tree (AST) to provide a "Confidence Score" for every dependency.

## Why Gnorise?

- **Context-Aware Security**: Don't panic over every CVE. Gnorise tells you if the vulnerable package is actually imported in your code.
- **Intelligent Cleanup**: Identifies unused packages with high precision, distinguishing between code dependencies and CLI tools (like ESLint).
- **Impact Analysis**: Predict exactly what will break if you remove a package, both in your code and in your dependency tree.
- **CI/CD Integration**: Automatically block PRs that introduce unused bloat or risky vulnerabilities.

## Installation

```bash
pip install gnorise
```

## Quick Start

```bash
# Get a high-level health summary
gnorise doctor

# Run a full scan of your project
gnorise scan

# Perform a context-aware security audit
gnorise audit

# Explain where a specific package is used
gnorise explain lodash

# See the impact of removing a package
gnorise impact axios
```

## Commands

### `scan`
Runs a deep analysis of your project. 
- `--json`: Get machine-readable output for custom tooling.
- `--ci`: Fails if high-confidence unused dependencies are found.

### `audit`
Queries the OSV database and cross-references results with your code usage.
- Shows "Used: Yes/No" for every vulnerability to help you prioritize fixes.

### `clean`
Lists all unused dependencies with a confidence score and generates the uninstall command for you.

## CI Integration

Gnorise is built for pipelines. Add it to your GitHub Actions or GitLab CI:

```yaml
- name: Gnorise Scan
  run: gnorise scan --ci
```

## How it Works

Gnorise uses **Tree-sitter** to parse your source code (JS/TS/JSX/TSX). It doesn't just look for strings; it understands the structure of your imports, `require()` calls, and dynamic imports to map your `package.json` to real-world usage.

---

> "Stop guessing your dependencies—understand them."
