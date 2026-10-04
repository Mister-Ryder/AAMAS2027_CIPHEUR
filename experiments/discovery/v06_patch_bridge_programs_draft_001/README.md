# Metadata-only bridge program inventory draft

Program inventory SHA-256: `cd3b541c76ff9da044f5e1c312936067f2741d4ad347d77ef38cb0a9a31d570c`.

Nineteen explicit identities are copied from the immutable R2/control selections. No program, conditional oracle, selector or scheduler was called. This draft is not an execution release. The four future frozen EoH identities must be appended in a new immutable complete inventory, preserving nulls and origins, before root authorizes the bridge. No evolving EoH file was read.

| Bridge role | Count |
|---|---:|
| witness_joint | 4 |
| witness_quality | 4 |
| relations_quality | 4 |
| objective_quality | 4 |
| fixed_structural | 1 |
| fixed_base | 1 |
| degree | 1 |

The Degree entry has no program AST because the bridge executes exact weight/patch-degree priorities; its original frozen Degree reference hash remains bound in metadata. The other eighteen entries preserve the original program objects and validated original program hashes. Guarded W and nonguarded quality-comparison roles remain distinct. Duplicate executable-field hashes, if any, remain separate identities rather than independent discoveries.

| Identity | Bridge role | Original frozen program SHA-256 |
|---|---|---|
| joint|block_0_witness:2 | witness_joint | `c210ae1446dfdc7248241131abd4624e70ea3051dc25077da04ca76f1693f8ad` |
| joint|block_1_witness:1 | witness_joint | `a716a96b2af013c7fed4ff8f52ec83fdc23e324937db73a51c76303bd46708ad` |
| joint|block_2_witness:0 | witness_joint | `55617ed694297b667e9f1e2fa3ee6214bea911f6a47d2cc7668c4a1fcf8201a0` |
| joint|block_3_witness:3 | witness_joint | `769787b97b77b1e44ddc2e4ec6b54ec33bf42c1089cef7a600c4473dd23138cb` |
| quality|block_0_witness:3 | witness_quality | `8d85b9cf6c5b9c0782e808fceedccfb18ff70ed563b8718743e3f331cf48a836` |
| quality|block_0_relations:0 | relations_quality | `55e08865d79d0510019e78af96d2ef95b55b76428641358936c90bbd3ea5f5b9` |
| quality|block_0_objective:7 | objective_quality | `302f728cfd0b61995357dc501acad3a57fd84096fcd30cf596bae5f8483a0057` |
| quality|block_1_witness:7 | witness_quality | `4a6318146926261eac1c64c1f0d77bfb88e6dc43696d0c77e4d4e6fe92be81d7` |
| quality|block_1_relations:1 | relations_quality | `93a6b177f49eebda35eb1530d0d01fb4675758f858ac7974097f88caa44e5bd9` |
| quality|block_1_objective:2 | objective_quality | `e749e4293204ab0e5d472e597022a9841dd65e8d9a2adf6e072e1dddc4b4d3ec` |
| quality|block_2_witness:6 | witness_quality | `0a702c3635266af99d83893bdf1c0a99be65ffdfc1b94ad9fe89315072ba05ff` |
| quality|block_2_relations:6 | relations_quality | `9638be7938a6ca49d8d2a115a18df1e491d5db357f17fcbce6b6c2eb7029a0da` |
| quality|block_2_objective:7 | objective_quality | `979b0f1d4d8b0fc1f631fdd64745e9bef0eb2cd90f750a7c1b2d787a221cec41` |
| quality|block_3_witness:5 | witness_quality | `9cc48549bd84f908469617f35f7b0561cdae6209cb2960b23ebc960463390f5f` |
| quality|block_3_relations:1 | relations_quality | `2cea947d068ce655244caece457a2fede3de2afe97decee1968d49918948b9bf` |
| quality|block_3_objective:5 | objective_quality | `0046e32254a1b5ffec9df50301d0a5abf1743d8eb031a169c844b03825e8ec9a` |
| control_0_enumerated_structural:1 | fixed_structural | `7bd78771bfdb8a54a21f5253489688aac6c4b6699578f0cbcadaf28ffdbab4f1` |
| control_0_fixed_base9:0 | fixed_base | `4956717e011da46628405f5faa8ef434e63eb8eb2d0851c3c95acee406ed401e` |
| fixed_degree | degree | `ab44c5f7481ddc4399fe567181fed9284e9255c45d074f525eecbdc6888443cb` |
