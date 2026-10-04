# V06 completed server TRAIN diagnostic

All120 original LLM positions and64 control repeats were retained. This is descriptive accounting, not a new assessor, selector or independent semantic audit. The four matched authoring blocks are1/2/3/4; the original block0 transport failure stays in the unconditional accounting. No ASTs, gates, scalar scores or TRAIN quality are edited.

| Block | Arm | Eligible /8 | Strict fit range /594 | Alias fit range /90 | Status |
|---:|---|---:|---|---|---|
|0|witness|1/8|[546, 579]|[73, 84]|{'assessed': 8}|
|0|relations|0/8|None|None|{'invalid_response_schema': 8}|
|0|objective|1/8|[560, 581]|[73, 84]|{'assessed': 8}|
|1|witness|2/8|[541, 580]|[74, 85]|{'assessed': 8}|
|1|relations|0/8|[534, 579]|[72, 84]|{'assessed': 8}|
|1|objective|1/8|[532, 579]|[72, 84]|{'assessed': 8}|
|2|witness|2/8|[549, 581]|[75, 84]|{'assessed': 8}|
|2|relations|2/8|[526, 584]|[73, 86]|{'assessed': 8}|
|2|objective|0/8|[476, 579]|[29, 81]|{'assessed': 8}|
|3|witness|2/8|[559, 581]|[73, 86]|{'assessed': 8}|
|3|relations|1/8|[561, 582]|[77, 85]|{'assessed': 8}|
|3|objective|1/8|[502, 579]|[40, 85]|{'assessed': 8}|
|4|witness|0/8|[556, 579]|[69, 82]|{'assessed': 8}|
|4|relations|1/8|[544, 582]|[68, 84]|{'assessed': 8}|
|4|objective|1/8|[554, 577]|[73, 85]|{'assessed': 8}|

The exact three empty matched cells are relations block1, objective block2 and witness block4. Nine genuine winners do not meet the registered twelve-winner performance barrier. TEST remains unexecuted, and missing programs cannot be substituted or repaired silently.

| Winner | Strict /594 | Alias /90 | Exact TRAIN Q | Exact work |
|---|---:|---:|---|---|
|block_1_witness:5|578|84|2693/4480|598975/72|
|block_1_objective:7|567|82|2693/4480|24514513/2880|
|block_2_witness:1|572|84|2693/4480|38262143/5760|
|block_2_relations:4|571|79|2693/4480|8367223/1152|
|block_3_witness:1|575|85|2693/4480|19288019/2880|
|block_3_relations:5|561|77|2693/4480|8927297/1152|
|block_3_objective:7|579|85|2693/4480|6259097/720|
|block_4_relations:6|575|84|2693/4480|10905137/1152|
|block_4_objective:2|577|85|2693/4480|24724423/2880|

Controls repeat the same16 ASTs four times; these are not independent authoring draws. Only block0 quality-only winners are declared for performance, without relabeling a failed joint gate.

| Control bank | Joint eligible /8 | Completed quality /8 | Joint winner | Quality-only winner |
|---|---:|---:|---|---|
|enumerated_structural|0|8|None|control_0_enumerated_structural:1|
|fixed_base9|0|8|None|control_0_fixed_base9:0|

Complete per-slot work/CPU/strict/alias/gate/kernel status, exact winner values and arm accounting are in `experiments/analysis/v06/synthesis_train_summary_v06_001.json`. Extracted original bytes and file hashes are in `experiments/discovery/v06_synthesis_server_001/EXTRACTION_RECEIPT.json`. Both phase logs and source/host/archive receipts remain in the immutable archive.

Raw archive SHA256: `c6b3b754aa0af36c769a4865e5f935085136f025d88665f079835dfc445f89d9`.
No scheduling/oracle/model calls were performed by this summary or extraction.
