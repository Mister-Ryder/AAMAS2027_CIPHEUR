# Exact-count compatibility for frozen V06 consumers

Three independently produced R2 reports use categorized `checks` dictionaries and empty `errors` lists. The frozen R2 held-out adapter expects an integer check count, and the native-performance identity binder expects `errors=0`. This mismatch was found before any TEST certificate or optimization call.

The original reports, frozen consumers, runtime sources, protocols, selections, observations and scientific gates remain byte-identical. `scripts/normalize_audit_receipt_v06.py` produces separate, explicit scalar receipts. It retains every non-count field exactly, saves the original categories and error records, and binds the original report and adapter bytes. Only the count representation changes: the original category sum becomes the integer `checks`, and the original empty list becomes `errors=0`. No new independent check, selection, search or discovery is performed.

The adapter requires actual nonnegative integer categories (rejecting booleans/floats), a positive consistent integer `total_checks`, an empty error list and integer zero `error_count`. Failed, inconsistent or already adapted reports cannot pass. Existing files cannot be overwritten. Four fabricated tests verify preservation, failure rejection, count-type consistency, byte binding and overwrite refusal.

| Original independent report | Original SHA-256 | Separate scalar-receipt SHA-256 | Actual checks |
| --- | --- | --- | ---: |
| `refinement_train_audit_v06_002.json` | `a3f8e33667c43e83a9f3199ea2f95fb8be0a7e29c968c017bfde8749aa1b5b34` | `fe2167f02c6720aa49143d1a9e064994bed0ca33aa538f8eef113e67f764e849` | 2,184,019 |
| `refinement_authoring_audit_v06_002.json` | `2c3327ae92e0deccabb054636bcabfd9e31ed317679837fc26b31243128b7f7c` | `43895916df80081ea0eaecbf0743a5dd1999e02ddd8c56cc86ee1372c4a9d5b3` | 479 |
| `refinement_packet_audit_v06_002.json` | `7cabb43f86f1346dfd7b0156c096fc05bfd70c6f24850ee663394137f803837c` | `b0ecae2f92522b42ff6b884cd8b1a0896984c3012904c041c0b5c3575ad14951` | 386 |

All files above are in `experiments/analysis/v06`; scalar receipts append `_scalar_receipt_001` to the original stem. Adapter source SHA-256 is `d22bb897f2170359e8acc73ec614522bbef70ef5aeeb855b46b0d1238163c457`.

Root requires an independent schema-only review, and its subsequent TEST release binds original reports, adapted receipts, adapter source and exact review bytes together. Numeric compatibility does not reopen R1's failed barrier or replace independent R2/EoH author/TRAIN audits. The metadata-only release helper also includes the original certificate runner's mandatory `selection_split=train`, `test_accessed=false` and four genuine W programs; certificate `programme_freeze_sha256` is the complete root-release byte hash. No TEST release has been issued when this explanation is written.
