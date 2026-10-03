# Substantial feature delivery preference

User instruction, 2026-10-03. This supersedes the earlier temporary request not to commit work.

For substantial changes/features in this project, complete implementation and appropriate verification,
write detailed documentation, then commit and push the feature branch. Documentation should cover the
problem and economic rationale, design choices and alternatives, interfaces and reproducible commands,
validation evidence, known limitations, and implemented versus proposed capabilities. Record failed
checks honestly, including inherited repository failures. Inspect the staged changes and scan for secrets.
Keep unrelated work out of the commit. Report the branch, commit and remaining limitations after delivery.

This authorizes feature commits and branch pushes; merging main, deploying and opening a sealed
out-of-sample window remain separate actions governed by their existing rules.

First delivery: src/unified_factors/ contains the factor baseline and CCC-GARCH implementation.
Its README.md routes to design, research hypotheses, contracts and validation documentation.
