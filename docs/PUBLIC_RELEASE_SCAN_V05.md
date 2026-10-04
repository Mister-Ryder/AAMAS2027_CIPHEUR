# V05 bounded public-release security review

Snapshot completed: 2026-10-03T11:29:05.243768+00:00; elapsed 151.906 seconds.

This review reads current tracked and nonignored untracked repository files, plus first-level repository-root ZIP/TAR containers. It checks first-level regular archive member streams without extraction or nested recursion. Git history, the on-disk ignored `.research` directory, server files and credentials outside this inventory were not accessed. No frozen file was modified.

Working-tree files read: 693 (273,671,601 bytes); direct signature streams: 649. Archive containers: 44; regular member streams scanned: 925 (2,345,763,565 decompressed bytes). V05 authoring-related direct streams: 18.

The rules detect sensitive filenames; encoded private-key material with headers and footers; known API-token prefixes; credential-bearing URL userinfo or long signed/token query values; and high-confidence quoted credential assignments. Direct binary content receives ASCII signature scanning, and detected UTF-16 text is also decoded. Regex literals and recognized illustrative placeholders are not credentials.

Finding path/category pairs: **0**. No matched values or credential excerpts are retained or printed.

No high-confidence credential signature or sensitive filename was found within the scanned content.

Nested archive members not opened: 7. Unread/special/scope-excluded entries: 0. Archive read completeness: 44/44 containers (within the declared nonnested scope).

This is a bounded working-tree release check, not a guarantee that the repository, all history, ignored files, remote systems or nested archives are secret-free. Short/custom/low-entropy secrets, unsupported encodings and arbitrary embedded media metadata can escape these signatures. Individual skipped paths and container completeness are recorded in the JSON receipt.

Scanner source SHA256: `4f0bfba31dfd174c8e692d89cfdaa9c4c04be4b1abece71058f1d3a65aed1566`. Input inventory SHA256: `789caf92995e4a41cffa8a4b8c6626a9248f562a810ba615a7c411673cf992b9`. First-level archive-member inventory SHA256: `b8526587d7144ea0bdc30cd04456216be4e554f7d3a276c1bce929430d865e83`.

Detailed receipt: `experiments/analysis/v05/release_security_v05.json`. Counts include all assigned inventory entries at scan start; self-generated scan receipts are excluded to avoid recursion. First-level archive content is checked as packaged, even if its internal names would normally be ignored on disk. No archive member was extracted or executed.

Post-scan detector smoke checks: **12/12 passed** using in-memory synthetic signatures (PEM and JSON escaping, provider tokens, URL userinfo/query, quoted assignments and UTF-16) and negative controls for regex literals and scientific SHA fields. No synthetic value is retained in the receipt.

## Final declared text delta

Completed: 2026-10-03T11:49:22.515921+00:00. Read **14** declared late-writing text files (**64,439 bytes**) with the same signature rules: **0 high-confidence findings**. No old archive was reopened; the full-scan counts above remain unchanged.

This delta includes final delivery/replay/authoring/review/design notes, README, version/package metadata, the V05 run ledger, both image-provenance receipts, `.gitattributes` and the manifest updater. Source, figures and paper were only read. Scientific scripts and programme selections were not changed. Final manifest generation remains a subsequent parent-agent action.

| Delta path | Bytes |
|---|---:|
| `.gitattributes` | 423 |
| `README.md` | 13618 |
| `autoresearch/loop-261003-v05/handoff.json` | 1401 |
| `autoresearch/loop-261003-v05/results.tsv` | 2401 |
| `cipheur/__init__.py` | 98 |
| `docs/AI_ASSISTANCE_V05.md` | 3727 |
| `docs/DELIVERY_V05.md` | 3788 |
| `docs/FIGURE_DESIGN_V05.md` | 4292 |
| `docs/FINAL_REVIEW_V05.md` | 5802 |
| `docs/REPLAY_V05.md` | 2436 |
| `paper/figures/IMAGEGEN_EARLY_PROVENANCE_V05.json` | 10245 |
| `paper/figures/IMAGEGEN_PROVENANCE_V05.json` | 13940 |
| `pyproject.toml` | 588 |
| `scripts/update_manifest.py` | 1680 |

Delta inventory SHA256: `25bccc757333ae36a8784e5b6069939a7151906a6fed9871794a2aed52428cb0`. Actual provenance JSON SHA256: `8147e8ffcad6eb4380bf9c96a594966bdd981909a70fddf925d999f2bf37e7b5`. The parent clarified that `1977c3db` identifies the mechanism PNG field rather than the JSON file. No credential value is recorded or printed; cryptographic source/manifest hashes are not credentials.

The bounded full-scan limitations continue to apply. This delta verifies only the listed final text and does not expand the review into all Git history, ignored/private data, nested archives or later unlisted edits.

## Stable late-presentation text delta

Completed after the explicit final-document-ready signal: 2026-10-03T12:29:59.846207+00:00. Read **12** declared late-presentation text files (**12,618,398 bytes**): **0 high-confidence findings**. Actual file SHA256 values are stored individually in `late_layout_delta.inventory`.

The original full scan and first 14-file delta remain unchanged; their canonical record hash was verified before and after this append. No archived member was decompressed again. The existing effect-curves JSON was included only because its builder-SHA receipt changed; no numeric result was recomputed or altered. No new presentation JSON was expected.

| Late-layout path | Bytes |
|---|---:|
| `README.md` | 13713 |
| `autoresearch/loop-261003-v05/results.tsv` | 2770 |
| `docs/COMPACT_FIGURES_V05.md` | 4630 |
| `docs/DELIVERY_V05.md` | 4090 |
| `docs/FIGURE_DESIGN_V05.md` | 5585 |
| `docs/FINAL_REVIEW_V05.md` | 6650 |
| `experiments/analysis/v05/effect_curves.json` | 12517137 |
| `paper/main.tex` | 9320 |
| `paper/sections/discussion.tex` | 1402 |
| `paper/sections/experiments.tex` | 9590 |
| `scripts/build_compact_figures_v05.py` | 14498 |
| `scripts/build_effect_curves_v05.py` | 29013 |

Late-layout inventory SHA256: `4f1ad54301cb4d3e787f87d25a4a6ba3198934102c59c48a354e24ea7f36a414`. All 11 source/docs/ledger targets have LF line endings. The existing numeric effect-curves JSON retains its original CRLF bytes; it was only read, and its actual SHA is recorded. That raw-receipt line ending is not a credential finding or a source-format repair request. These two scan reports were written as LF UTF-8. No credential value or sensitive example is retained or printed; cryptographic builder/manifest hashes are not treated as credentials.

The review changed only these two scan reports. Paper, discussion/balance placement, plots, plot builders, programme selections and frozen scientific observations were only read. This remains a bounded current-text security check rather than a guarantee for all history, ignored/private data, nested archives or subsequent unlisted changes. Final manifest/staging/publication are subsequent parent-agent actions.
