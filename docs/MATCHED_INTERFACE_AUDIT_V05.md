# V05 authoring interface audit note

This is an engineering and experimental-method limitation report, not paper content. It was written after all twelve authoring outputs were frozen and before their completed TRAIN/TEST assessment was inspected.

All twelve registered masked packets contain this shared operation note:

> Typed feature division uses a signed near-zero guard; use explicit max guards in the Python ranking rule.

The frozen `graph_features.py` implementation instead rejects exactly-zero denominators for typed `div` and divides normally otherwise. `compiled.py` delegates these graph-expression operations to the same feature implementation. The authoring packet therefore misdescribes feature division. This is a common interface defect across all three arms, not an arm-specific change. It is relevant to validity/completion and must not be concealed if a generated feature divides by zero.

The original protocol, packets, responses, source snapshot, gate and selector remain unchanged. The independent verifier follows the actual frozen division semantics. Invalid runtime slots remain failed assignments with no repair or replacement. This note does not authorize outcome-conditioned salvage, a new authoring round, a source fix or selection after TEST.

A future study should preregister a corrected operation description before generating any new candidates and use genuinely new confirmation inputs. Current pilot conclusions must stay within the shared imperfect prompt interface.
