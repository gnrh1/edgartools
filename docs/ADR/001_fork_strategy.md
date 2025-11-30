# ADR 001: Fork Strategy and Divergence Management

## Status
Accepted

## Date
2025-11-30

## Context
This repository is a fork of `dgunning/edgartools` (version 4.0.0). The upstream repository has advanced significantly (version 4.33.1+) and has a completely unrelated git history, making a standard `git merge` impossible without catastrophic conflicts (see `UPSTREAM_ISSUE.md`).

However, we need to maintain and enhance this codebase for our specific use cases (e.g., the dashboard, specific pipeline logic) while occasionally fixing bugs in the core library or cherry-picking critical upstream features.

## Decision
1.  **Hard Fork Maintenance**: We will treat this repository as a "hard fork". We will not attempt to synchronize with upstream via `git merge`.
2.  **Divergence Log**: We will maintain a `docs/DIVERGENCE_LOG.md` file to track *every* modification made to the core `edgar/` library code. This allows us to:
    *   Distinguish our custom logic from the original library code.
    *   Easily identify what changes might need to be re-applied if we ever migrate to a newer upstream version (e.g., via a fresh fork and copy-paste).
3.  **Project Code Separation**: All project-specific code (pipelines, dashboards, scripts) should reside *outside* the `edgar/` directory whenever possible.
4.  **Upstream Contributions**: If we fix a generic bug (like the `datetime.date` issue), we should consider submitting a PR to the upstream repository, even if we can't pull the changes back immediately.

## Consequences
-   **Pros**:
    -   Stability: We control our own destiny and avoid breakage from upstream changes.
    -   Clarity: We know exactly what we've changed in the core library.
-   **Cons**:
    -   Maintenance Burden: We miss out on upstream improvements unless manually ported.
    -   Drift: Over time, our version of `edgartools` will diverge further from the community standard.

## Compliance
-   Any PR that modifies files within `edgar/` MUST include an entry in `docs/DIVERGENCE_LOG.md`.
