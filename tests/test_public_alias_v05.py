from __future__ import annotations

from fractions import Fraction
import unittest

from cipheur.experiment_data import diagnostic_pair
from cipheur.graph_features import FeatureRuleProgram
from cipheur.model import Contact, Graph
from cipheur.public_alias_v05 import base_alias_pairs, induced_subset, run_state


class PublicAliasV05Tests(unittest.TestCase):
    def test_competing_aliases_require_all_nine_exact_fields(self):
        g=Graph("triangle",tuple(Contact(str(i),1,"s","g",i,i+1) for i in range(3)),frozenset({("0","1"),("1","2"),("0","2")}))
        pairs,total=base_alias_pairs(g,2)
        self.assertEqual(total,3)
        self.assertEqual([(p["a"],p["b"]) for p in pairs],[("0","1"),("0","2")])
        self.assertTrue(all(p["a_base9"]==p["b_base9"] for p in pairs))
        contacts=list(g.contacts);contacts[0]=Contact("0",1,"s","g",0,1.5)
        different=Graph("duration_changed",tuple(contacts),g.edges)
        _,total=base_alias_pairs(different,8)
        self.assertEqual(total,1)

    def test_source_subset_is_hash_deterministic_and_preserves_induced_edges(self):
        g=Graph("cycle",tuple(Contact(str(i),1,"s","g",i,i+1) for i in range(40)),frozenset((str(i),str((i+1)%40)) for i in range(40)))
        a=induced_subset(g,"source",32,"salt");b=induced_subset(g,"source",32,"salt")
        self.assertEqual(a.digest(),b.digest())
        self.assertEqual(len(a.nodes),32)
        self.assertEqual(a.edges,frozenset(e for e in g.edges if set(e)<=a.nodes.keys()))
        self.assertEqual(a.provenance["source_graph_digest"],g.digest())
        self.assertNotEqual(induced_subset(g,"source",32,"different").digest(),a.digest())

    def test_proved_small_alias_and_unknown_both_retained(self):
        p=diagnostic_pair("train",0,"reversal");g=p["left"]
        # The motif has an isolated fixed node. Initial aliases remain valid;
        # its common optimum cancels, exactly as in full graph semantics.
        queries,total=base_alias_pairs(g,8)
        self.assertTrue(any({r["a"],r["b"]}=={p["a"],p["b"]} for r in queries))
        record={"id":"test","track":"fixture","source_id":"fixture","cluster":"fixture","graph":g.to_dict(),
                "graph_digest":g.digest(),"fixed":[],"excluded":[],"queries":queries,"query_shortfall":8-len(queries),"scope":"unit fixture"}
        program=FeatureRuleProgram("weight",[],"weight","test").to_dict()
        config={"oracle":{"nodes_per_component":2048,"max_search_component":256,"max_nodes":16384,"max_calls":32},
                "epsilon":1e-8,"enforce_wall_cap":False}
        result=run_state((record,config,program))
        self.assertEqual(len(result["rows"]),len(queries))
        strict=[r for r in result["rows"] if r["base_representation_self_loop"]]
        self.assertTrue(strict)
        self.assertTrue(all(r["primary_strict_pair_agreement"] is False for r in strict))
        config["oracle"]["max_calls"]=0
        result=run_state((record,config,program))
        self.assertTrue(any(r["difference"]["status"]=="unknown" for r in result["rows"]))
        self.assertEqual(len(result["rows"]),len(queries))


if __name__=="__main__":unittest.main()
