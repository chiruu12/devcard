# DevCard Repo Architecture

## Overview

DevCard is a GitHub profile intelligence pipeline with three user-facing surfaces:

- a CLI that generates and renders developer cards
- an MCP server that lets agents query and compare developers
- audit/fix workflows that score profiles and optionally apply GitHub changes

The central design choice is a shared `DevCard` domain model. The repo has multiple interfaces, but only one core data contract.

## Subsystems

### 1. Entrypoints

- `src/devcard/cli.py` is intentionally thin. It parses flags, creates config, calls pipeline functions, then picks an output adapter.
- `devcard-mcp/src/devcard_mcp/server.py` is another thin wrapper. It exposes tools, manages a small cache, and delegates to the root package.

### 2. Core Orchestration

- `src/devcard/pipeline.py` is the orchestration center.
- It owns generation, audit scoring, and fix workflows.
- This is the main concentration-of-responsibility risk in the current design.

### 3. Domain Model

- `src/devcard/models.py` defines the canonical Pydantic models.
- `DevCard` is the internal assembly target and the external JSON contract.
- Audit and fix flows add adjacent models such as `AuditResult`, `Issue`, `RepoAnalysis`, and `FixResult`.

### 4. GitHub Boundary

- `src/devcard/github/client.py` isolates all GitHub API interaction.
- The client handles auth headers, caching for GETs, limited rate-limit recovery, and write operations for file creation and metadata updates.
- This keeps extractors and analyzers mostly HTTP-agnostic.

### 5. Extraction Layer

- Extractors convert raw GitHub data into typed signals.
- Most are best-effort and degrade to `None` rather than aborting the whole run.
- Shared fetches, especially root listings, are reused across extractors to control API cost.

### 6. Analysis Layer

- Analyzers are post-processing heuristics, not source-of-truth fetchers.
- They classify developer type, project type, contribution style, and compute quality or readiness scores.
- The repo is largely heuristic-driven and mapping-driven by default.

### 7. Output Layer

- Renderers and output adapters convert one `DevCard` into multiple human and agent representations.
- This keeps the generation pipeline stable while allowing new surfaces to be added without changing extraction logic.

## Repo Shape

- `src/devcard/`: core library and CLI
- `devcard-mcp/src/devcard_mcp/`: MCP adapter package
- `schema/`: JSON schema contract and examples
- `mappings/`: heuristic lookup tables and rule sets
- `tests/`: root package tests
- `devcard-mcp/tests/`: MCP package tests
- `context/architecture/`: architecture notes tied to current implementation

## Refactor Priorities

### 1. Split `pipeline.py` by responsibility

Recommended target structure:

- generation orchestration
- audit/scoring orchestration
- fix/mutation orchestration
- shared fetch helpers

This is the highest-value refactor because it reduces change coupling across the CLI, MCP, and fixer paths.

### 2. Tighten the package boundary between `devcard` and `devcard-mcp`

- The MCP package is intentionally thin, which is good.
- The weak point is test/runtime packaging ergonomics, not domain duplication.
- Keep the MCP layer adapter-only and avoid moving business logic into it.

### 3. Continue moving heuristics into explicit mapping or rule files

- This repo already uses YAML mappings well.
- Expanding that pattern will make behavior easier to tune without broad code edits.

### 4. Separate read-only intelligence from mutation workflows

- Audit/fix functionality is useful, but it changes the trust and safety profile of the tool.
- Keeping mutation orchestration isolated will help testing, future permissions, and MCP tool clarity.

## Current Testing Notes

- Root tests pass from the repo root.
- MCP tests pass from `devcard-mcp/`.
- The repo now includes root-level path setup so both suites can be run together from the root without package import collisions.
