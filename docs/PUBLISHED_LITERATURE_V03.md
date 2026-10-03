# Published literature and comparison audit for revision V03

Verified on **3 October 2026**. This audit accompanies `paper/references_v03.bib` and `paper/sections/related_work.tex`. The bibliography contains 25 published references. Publisher records, official proceedings, and final published PDFs supply the metadata and technical comparisons. Author-hosted final publication PDFs were used only where publisher retrieval was restricted. No preprint-only item is promoted to a conference or journal publication.

The user-approved title and abstract remain in `paper/ABSTRACT_TARGET.md`; this literature work does not change them. Numerical superiority claims require the revision's own completed experiments and are deliberately absent from the comparison matrix below.

## Exact identity and organization of the supplied PDFs

### VEXW9837.pdf

**Universal Solvability for Robot Motion Planning on Graphs**, Anubhav Dhar, Pranav Nyati, Tanishq Prasad, Ashlesha Hota, and Sudeshna Kolay. AAMAS 2026, full research paper, pp. 947–955, DOI **10.65109/VEXW9837**. [Official published PDF](https://www.ifaamas.org/Proceedings/aamas2026/pdfs/VEXW9837.pdf).

This is a graph-planning theory paper. It concerns universal robot-motion reachability, structural equivalences, algorithmic conditions, and augmentation bounds. It contains no satellite scheduling or LLM algorithm synthesis study and no experimental evaluation section. It must not be described as an experimental precedent.

Its presentation is useful: §1 introduces a small NO/YES witness graph and enumerates scoped results; §2 fixes moves, an equivalence, and boxed input/question definitions; §3 develops accumulation; §§4–5 distinguish randomized and deterministic algorithms; §6 gives augmentation bounds; §7 concludes. Five diagrams illustrate a counterexample, a move, permutation composition, a structural transformation, and a bound witness. For this revision, the transferable lesson is to expose the exact obstruction with a small concrete graph, then attach the theorem and algorithm to that obstruction. The scheduling paper still needs its own empirical evidence.

Local extraction and visual inspection are in ignored `.research/VEXW9837.txt` and `.research/vexw-page*.png`.

### SBAY6258.pdf

**DRAGON: LLM-Driven Decomposition and Reconstruction Agents for Large-Scale Combinatorial Optimization**, Shengkai Chen et al. AAMAS 2026, full research paper, pp. 2809–2817, DOI **10.65109/SBAY6258**. [Official published PDF](https://www.ifaamas.org/Proceedings/aamas2026/pdfs/SBAY6258.pdf). The detailed prior review remains in `docs/DRAGON_REVIEW.md`.

The published system uses per-instance decomposition and reconstruction agents, boundary constraints, checker feedback, and retained experience. Its benchmarks include TSP, CVRP, bin packing, and multidimensional knapsack. Context awareness and feedback are already present. Its system diagram and component ablations motivate separately evaluating information, rule synthesis, and cost in the revision. A fair comparison charges discovery plus deployment and states the deployment count used for amortization.

## Primary publication register

| Bib key | Verified publication | Primary record and role |
|---|---|---|
| `augenstein2016optimal` | ICAPS 2016, 26(1):345–352; **Novel Applications Track** | [AAAI publisher](https://ojs.aaai.org/index.php/ICAPS/article/view/13784). Constellation imaging/downlink optimization; label the track accurately. |
| `levinson2025optimal` | IJCAI 2025 **Main Track**, 8544–8553 | [IJCAI proceedings](https://www.ijcai.org/proceedings/2025/950). Integrated collection/downlink planning with limited storage. |
| `tao2023transmitting` | ACM MobiCom 2023 | [Published DOI](https://doi.org/10.1145/3570361.3592521); [author-hosted final PDF](https://deepakv.web.illinois.edu/assets/papers/umbra_mobicom_23.pdf). Umbra; future contacts and queues matter to throughput. |
| `khalil2017learning` | NeurIPS 2017, volume 30 | [Official proceedings](https://proceedings.neurips.cc/paper_files/paper/2017/hash/d9896106ca98d3d05b8cbdf4fd8b13a1-Abstract.html). Structure2vec and constructive graph optimization. |
| `li2018gcn` | NeurIPS 2018, volume 31 | [Official proceedings](https://proceedings.neurips.cc/paper/2018/hash/8d3bba7425e7c98c50f52ca1b52d3735-Abstract.html). GCN prediction and guided tree search. |
| `gasse2019exact` | NeurIPS 2019, volume 32 | [Official proceedings](https://proceedings.neurips.cc/paper/2019/hash/d14c2267d848abeb81fd590f371d39bd-Abstract.html). Learned branching inside an exact optimization framework. |
| `ahn2020defer` | ICML 2020, PMLR 119:134–144 | [PMLR](https://proceedings.mlr.press/v119/ahn20a.html). Learned deferral for maximum independent sets. |
| `li2024factor` | AAMAS 2024 full research, 1165–1173 | [Official PDF](https://www.ifaamas.org/Proceedings/aamas2024/pdfs/p1165.pdf). Factor-graph neural inference and Max-Sum for route planning. |
| `bai2025local` | AAMAS 2025 full research, 188–196 | [Official PDF](https://www.ifaamas.org/Proceedings/aamas2025/pdfs/p188.pdf). Local topology for generalizable neural TSP methods. |
| `xu2019powerful` | ICLR 2019 | [Official OpenReview record](https://openreview.net/forum?id=ryGs6iA5Km); [ICLR program](https://iclr.cc/Conferences/2019/Videos). GNN aggregation expressiveness. |
| `morris2019weisfeiler` | AAAI 2019, 33(1):4602–4609 | [AAAI publisher](https://ojs.aaai.org/index.php/AAAI/article/view/4384). Higher-order GNNs and Weisfeiler–Leman distinctions. |
| `giacomarra2025certified` | AAMAS 2025 full research, 877–885 | [Official PDF](https://www.ifaamas.org/Proceedings/aamas2025/pdfs/p877.pdf). Formal guidance for deep generative planning; a different certificate target. |
| `dhar2026universal` | AAMAS 2026 full research, 947–955 | [Official PDF](https://www.ifaamas.org/Proceedings/aamas2026/pdfs/VEXW9837.pdf). Structural graph-planning theory and witness diagrams. |
| `chen2026dragon` | AAMAS 2026 full research, 2809–2817 | [Official PDF](https://www.ifaamas.org/Proceedings/aamas2026/pdfs/SBAY6258.pdf). Instance-wise LLM decomposition and reconstruction. |
| `liu2024eoh` | ICML 2024, PMLR 235:32201–32223 | [PMLR](https://proceedings.mlr.press/v235/liu24bs.html). Evolves heuristic explanations and executable code. |
| `ye2024reevo` | NeurIPS 2024, volume 37 | [Official proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/4ced59d480e07d290b6f29fc8798f195-Abstract-Conference.html). Reflective heuristic evolution. |
| `romeraparedes2024funsearch` | Nature 2024, 625:468–475 | [Nature](https://www.nature.com/articles/s41586-023-06924-6). Published online 14 December 2023; cite the 2024 volume year. |
| `liu2026eohs` | AAAI 2026, 40(43):37090–37098 | [AAAI publisher](https://ojs.aaai.org/index.php/AAAI/article/view/41038). Published 14 March 2026; evolves complementary heuristic sets. |
| `gong2026lace` | Nature Machine Intelligence, **published 1 October 2026** | [Nature version of record](https://www.nature.com/articles/s42256-026-01307-8), DOI **10.1038/s42256-026-01307-8**. Published by this audit date, 3 October 2026. |
| `clarke2000cegar` | CAV 2000, LNCS 1855:154–169 | [Springer proceedings chapter](https://link.springer.com/chapter/10.1007/10722167_15). Classical counterexample-guided abstraction refinement. |
| `jha2010oracle` | ICSE 2010, 215–224 | [Published DOI](https://doi.org/10.1145/1806799.1806833); [author publication record](https://people.eecs.berkeley.edu/~sseshia/pubs/b2hd-jha-icse10.html). Oracle-guided component synthesis with examples and SMT. |
| `ellis2021dreamcoder` | PLDI 2021, 835–850 | [Published DOI](https://doi.org/10.1145/3453483.3454080); [final publication PDF](https://people.csail.mit.edu/asolar/papers/EllisWNSMHCST21.pdf). Learned libraries and synthesis guidance. |
| `bonet2019features` | AAAI 2019, 33(1):2703–2710 | [AAAI publisher](https://ojs.aaai.org/index.php/AAAI/article/view/4120). Learning symbolic features and abstract actions for generalized plans. |
| `frances2021policies` | AAAI 2021, 35(13):11801–11808 | [AAAI publisher](https://ojs.aaai.org/index.php/AAAI/article/view/17402). Joint feature selection and good/bad transition classification. |
| `chvatal1979greedy` | Mathematics of Operations Research 1979, 4(3):233–235 | [INFORMS](https://pubsonline.informs.org/doi/10.1287/moor.4.3.233). Published 1 August 1979; classical weighted-set-cover greedy guarantee. |

Metadata decisions: the final NeurIPS 2017 PDF lists Hanjun Dai before Elias Khalil, whereas its landing-page display differs; the bibliography follows the published PDF. PMLR's EoH export splits Xialiang Tong incorrectly; the final published author name is used. The AAAI 2021 publisher record includes “Planning” in the Francès et al. title, whereas the PDF title is shorter; the bibliography follows the publisher record. Unavailable article pagination is omitted rather than guessed. LACE currently has no verified volume/page range in the publisher record used here.

## Polished novelty comparison matrix

These rows are suitable for a reviewer-facing comparison table. “Revision mechanism” states the proposed implemented contract, not an unmeasured improvement. No row asserts that a prior method could never adopt the mechanism.

| Published comparison | Established capability and relevant overlap | Revision mechanism and defensible distinction |
|---|---|---|
| Satellite planning: Augenstein et al. (ICAPS 2016), Levinson et al. (IJCAI 2025), Umbra (MobiCom 2023) | Operational resources, temporal structure, and imaging/downlink interactions already determine schedule quality. | Within a pairwise-conflict contact-selection model, diagnose which observable graph distinctions support reusable ranking across static resource configurations. This is an information-design question; it does not replace integrated mission planning. |
| Dai et al. (NeurIPS 2017), Li et al. (NeurIPS 2018), Ahn et al. (ICML 2020) | Learned graph policies, search, and deferred decisions already adapt optimization decisions to structural context. | Expose exact equality of the scorer's complete feature vector, then use certified strict-ranking relations to detect finite-sample information obstructions before synthesizing a pointwise scorer. |
| Xu et al. (ICLR 2019), Morris et al. (AAAI 2019) | Aggregation architectures have explicit structural indistinguishability limits. | The quotient is induced by an explicitly specified feature interface on decision occurrences. A directed strict-ranking cycle witnesses inconsistency for that interface; the result is scoped to deterministic pointwise scoring, not all GNNs or graph policies. |
| FunSearch (Nature 2024), EoH (ICML 2024), ReEvo (NeurIPS 2024) | Executable-function search, explanation/code evolution, and reflective feedback already support offline heuristic discovery. | Certified residual relations distinguish insufficient information from an incorrect rule. Concrete equality-join witnesses drive feature repair, and ranking-rule realization is evaluated separately from representation adequacy. |
| EoH-S (AAAI 2026) | Complementary heuristic sets already address heterogeneous instance needs. | The refinement unit is a missing observable distinction exposed by a relation cycle. Portfolio diversity alone is not the proposed contribution. |
| LACE (Nature Machine Intelligence, 1 October 2026) | Its published abstract states a verified input/output/tool/portfolio interface and time-constrained complementary heuristic evolution. | The distinctive target is conditional-ranking evidence and quotient-cycle separation with a finite feature catalogue. The available abstract does not justify a claim that LACE lacks all representation refinement or formal checks. |
| DRAGON (AAMAS 2026) | Per-instance decomposition and reconstruction communicate boundary constraints and use checker feedback. | Feasible boundary replay yields certified residual ranking evidence for offline feature/rule refinement. Compare actual discovery and deployment cost, including amortization; the difference in online LLM use alone is not a quality or cost result. |
| CEGAR (CAV 2000) | Counterexamples already identify spurious behavior caused by abstraction and guide refinement. | The abstraction is a scheduling ranking interface. A concrete witness records strict relations and equality joins; a finite-catalogue cost master proposes feature refinements, followed by full quotient separation. This is a domain-specific refinement contract. |
| Bonet et al. (AAAI 2019), Francès et al. (AAAI 2021) | Symbolic features and generalized policies can already be learned jointly; transition separation is an established device. | Conditional-completion ranking relations and equality-join cycles determine the obstruction. Selected features must separate concrete cycle joins, and the complete quotient is rebuilt to find new conflicts. Joint feature learning itself is inherited. |
| DreamCoder (PLDI 2021), Jha et al. (ICSE 2010) | Component libraries, examples, and synthesis guidance already constrain reusable executable program search. | A scheduling-specific feature catalogue and rule language are linked through certified relation evidence, while information sufficiency, language realizability, and complete-schedule reward remain separate tests. |
| Chvátal (Mathematics of Operations Research 1979) | Weighted-set-cover greedy has a harmonic approximation guarantee under positive additive costs. | Any retained-witness cover guarantee is inherited and explicitly scoped. Full quotient rechecks are needed to discover cycles outside that retained family; shared computation requires a different cost accounting. |

## Formal claim boundaries for integration

- A quotient cycle is an information obstruction only when all strict relations are sound and the quotient uses the complete vector visible to the deterministic pointwise scorer. Hidden state or arbitrary tie-breaking must not silently enlarge the interface.
- Acyclicity removes the observed finite-data obstruction. It does not establish realizability in a restricted ranking DSL, optimality of greedy deployment, or out-of-distribution generalization.
- The finite feature master must separate concrete equality joins and then rebuild/recheck the full quotient. Covering one retained cycle family is not, by itself, a proof of complete repair.
- The classical `chvatal1979greedy` citation supports an **H_m** weighted-set-cover guarantee for a fixed, coverable universe of m retained witnesses and positive additive costs. It does not automatically bound nonadditive shared-DAG work or certify absence of unseen cycles. Generic catalogue hardness and restricted DSL realizability are distinct claims.
- Resource configurations are static per instance. Boundary replay and trajectory evidence must preserve feasibility, use the same intervention semantics, and abstain when bounds cannot certify a strict relation.
- The incremental shared feature DAG is a deployment mechanism. Its actual primitive work and runtime need measurement; an additive feature-selection surrogate must be labelled as such.

## AAMAS 2024–2026 coverage and excluded records

The inspected official AAMAS 2024 and 2025 tables of contents contain no paper title with “Satellite”; this title search is not proof that no relevant work exists. Verified 2024/2025 graph-optimization full papers are included above rather than relabelled as satellite work.

AAMAS 2026 also publishes **Large-Scale Continual Scheduling and Execution for Dynamic Distributed Satellite Constellation Observation Allocation: Extended Abstract**, Itai Zilberstein and Steve Chien, pp. 3158–3160, DOI **10.65109/JCYH5778**. [Official PDF](https://www.ifaamas.org/Proceedings/aamas2026/pdfs/JCYH5778.pdf). It concerns continual distributed scheduling/execution, which differs from the revision's frozen program under static per-instance configurations. Its **extended-abstract** status must be preserved. It is not included in the 25-entry main bibliography because the user's publication-quality floor should not be silently interpreted as admitting every track.

The AAMAS 2021 **Blue Sky Ideas Track** paper *Autonomous Agents and Multiagent Systems Challenges in Earth Observation Satellite Constellations* provides broad motivation, but is also omitted from the main bibliography. [Official PDF](https://www.ifaamas.org/Proceedings/aamas2021/pdfs/p39.pdf).

`yang2025heuragenix` is excluded because a final qualifying publication was not verified. `pereira2026property` is excluded because an accepted/preprint author page does not establish an accessible final NeurIPS 2026 proceedings record at this audit date. These exclusions concern verification and publication status; no negative technical claims about either work are inferred.

LACE is the important recent exception: its official Nature Machine Intelligence page explicitly identifies **1 October 2026** publication, so it is included. The full article was behind subscription access during this audit. Comparison claims therefore use only the official abstract and verified bibliographic record; supplementary algorithms, ablations, and unseen implementation details are not asserted.

## Integration and verification

The related-work fragment uses 20 distinct bibliography keys and approximately 500 words, arranged around satellite scheduling, learned representations, algorithm discovery, and abstraction/synthesis. Four additional references are available for the introduction or methods: `li2018gcn`, `gasse2019exact`, `giacomarra2025certified`, and `jha2010oracle`; `chvatal1979greedy` supports the feature-master approximation discussion. Avoid adding citations simply to maximize counts.

The new files contain no preprint URL, `eprint`, `archivePrefix`, or miscellaneous preprint bibliography entry. Every citation in the fragment resolves to `references_v03.bib`; keys are unique. The root author should integrate the fragment and bibliography and perform the complete multi-file LaTeX build. No quantitative baseline advantage has been invented in this audit.
