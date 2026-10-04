"""Compact, separate scientific panels from independently verified server data.

No policy, solver, conditional oracle, selection or resampling is executed here.
All quantities are restricted to the fixed TRAIN expression catalogue.
"""
from __future__ import annotations
from hashlib import sha256
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "experiments/analysis/v06/catalogue_cost_audit_v06_001.json"
EXPECTED = "b485a74414364e551abebc250dd6922498865a0a41ed93a8523ab4a559f5e0d2"
OUT = ROOT / "paper/figures"
BLUE, PURPLE, ORANGE, GRAY, INK = "#176B9B", "#71559C", "#D36B32", "#687782", "#243640"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def build():
    assert digest(AUDIT) == EXPECTED, "Independent catalogue audit bytes changed"
    audit = json.loads(AUDIT.read_bytes())
    assert audit["passed"] and not audit["errors"]
    assert digest(ROOT / audit["archive"]["path"]) == audit["archive"]["sha256"]
    case = next(c for c in audit["cases"] if c["id"] == "full_53")
    assert case["current_subset_is_acyclic"] and len(case["trace"]) == 9
    assert case["selected_indices"] == [4, 16, 27, 29]
    font_manager.findfont("Arial", fallback_to_default=False)
    plt.rcParams.update({"font.family": "Arial", "font.size": 9,
        "axes.labelsize": 9, "axes.titlesize": 9, "xtick.labelsize": 9,
        "ytick.labelsize": 9, "legend.fontsize": 8.5, "pdf.fonttype": 42,
        "ps.fonttype": 42, "axes.spines.top": False, "axes.edgecolor": GRAY,
        "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK,
        "ytick.color": INK, "figure.facecolor": "white", "savefig.facecolor": "white"})
    OUT.mkdir(parents=True, exist_ok=True)
    outputs, arrays, checks = {}, {}, []

    # A master is re-solved, so selected cost/alias counts need not be monotone.
    rounds = np.arange(10)
    costs = np.array([0] + [int(t["cost_exact"]) for t in case["trace"]])
    loops = np.array([90] + [t["quotient"]["self_loop_requirements"] for t in case["trace"]])
    cyclic = np.array([True] + [not t["quotient"]["acyclic"] for t in case["trace"]])
    assert loops[7:].tolist() == [0, 0, 0] and cyclic.tolist() == [True]*9+[False]
    fig = plt.figure(figsize=(3.35, 1.94))
    ax = fig.add_axes([.155, .24, .68, .58]); other = ax.twinx()
    ax.grid(axis="y", alpha=.15, linewidth=.5)
    line, = ax.plot(rounds, costs/1e6, color=BLUE, lw=1.25, marker="o", ms=3,
        markerfacecolor="white", label="Additive work")
    second, = other.plot(rounds, loops, color=ORANGE, lw=1.1, ls="--", marker="s", ms=2.8,
        label="Self-loops")
    ax.scatter([9], [costs[-1]/1e6], s=26, facecolors=PURPLE, edgecolors=PURPLE,
        linewidths=.8, zorder=5)
    ax.axvspan(6.8, 8.25, color=PURPLE, alpha=.07, linewidth=0)
    ax.set(xlim=(-.2,9.25), ylim=(-.025,1.52), xticks=[0,2,4,6,7,8,9],
        xlabel="Master solution", ylabel="Standalone work (million)")
    other.set(ylim=(-2,95), yticks=[0,30,60,90], ylabel="Self-loop requirements")
    other.spines["top"].set_visible(False)
    ax.tick_params(length=3,pad=2); other.tick_params(length=3,pad=2)
    ax.xaxis.labelpad=3; ax.yaxis.labelpad=3; other.yaxis.labelpad=2
    handles=[line,second,plt.Line2D([],[],color=PURPLE,marker="o",lw=0,ms=4,label="Full DAG")]
    fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.5,1.005),
        frameon=False,ncol=3,handlelength=1.2,columnspacing=.65,handletextpad=.3)
    np.testing.assert_array_equal(line.get_xdata(),rounds)
    np.testing.assert_array_equal(line.get_ydata(),costs/1e6)
    np.testing.assert_array_equal(second.get_ydata(),loops)
    checks += ["all10 cost/self-loop arrays equal audited server trace",
        "solutions7,8 cyclic despite0selfloops; solution9fullDAG"]
    arrays["refinement_cost_curve_v06"]={"round":rounds.tolist(),"cost_exact":costs.tolist(),
        "self_loop_requirements":loops.tolist(),"cyclic":cyclic.tolist()}
    for ext in ("pdf","png"):
        path=OUT/f"refinement_cost_curve_v06.{ext}"; fig.savefig(path,dpi=300)
        outputs[path.relative_to(ROOT).as_posix()]=digest(path)
    plt.close(fig)

    # Costs below are actual separate-expression charges, not deployment time.
    feature_work = np.array([29964,147167,394682,799655],dtype=np.int64)
    assert int(feature_work.sum()) == int(case["current_subset_cost_exact"])
    labels=[r"$g(N(v)\cup\{v\})$",r"$g(A\setminus\{v\})$",r"$|E(T(v))|$",r"$c(T(v))$"]
    fig=plt.figure(figsize=(3.35,1.94)); ax=fig.add_axes([.38,.25,.59,.60])
    bars=ax.barh(np.arange(4),feature_work/1e6,height=.52,
        color=[BLUE,PURPLE,GRAY,ORANGE],edgecolor="white",linewidth=.5)
    ax.invert_yaxis(); ax.set(yticks=np.arange(4),yticklabels=labels,
        xlim=(0,1.10),xticks=[0,.3,.6,.9],xlabel="Standalone work (million)")
    ax.spines["right"].set_visible(False); ax.tick_params(length=3,pad=2)
    ax.grid(axis="x",alpha=.15,lw=.5); ax.set_axisbelow(True)
    for b,w in zip(bars,feature_work):
        ax.text(b.get_width()+.014,b.get_y()+b.get_height()/2,
            f"{100*w/feature_work.sum():.1f}%",va="center",ha="left",fontsize=8)
    np.testing.assert_array_equal([b.get_width() for b in bars],feature_work/1e6)
    arrays["refinement_feature_work_v06"]={"index":[4,16,27,29],
        "cost_exact":feature_work.tolist(),"scope":"fresh standalone expression operation counts"}
    checks.append("selected4work sums equal independently certified minimum1371468")
    for ext in ("pdf","png"):
        path=OUT/f"refinement_feature_work_v06.{ext}"; fig.savefig(path,dpi=300)
        outputs[path.relative_to(ROOT).as_posix()]=digest(path)
    plt.close(fig)
    receipt={"version":"v06_catalogue_figures_001","independent_audit_sha256":EXPECTED,
        "server_archive_sha256":audit["archive"]["sha256"],"script_sha256":digest(__file__),
        "font":"Arial9pt at native3.35in width","outputs":outputs,"arrays":arrays,
        "checks":checks,"optimization_or_oracle_or_policy_execution":False,
        "TRAIN_only":True,"TEST_accessed":False,
        "scope":"fixed53-expression catalogue,594strict requirements; not learned scalar fit or scheduling gain"}
    dest=ROOT/"experiments/analysis/v06/catalogue_figures_v06_001.json"
    dest.write_bytes((json.dumps(receipt,indent=2,allow_nan=False)+"\n").encode())
    print(json.dumps({"panels":len(arrays),"checks":len(checks),"receipt_sha256":digest(dest)}))


if __name__ == "__main__":
    build()
