"""Presentation-only full-five-block information-gate yield panel.

Original-slot prefixes are bookkeeping, not sequential learning iterations.
No evaluation, oracle, candidate selection, inference or TEST read occurs.
"""
from hashlib import sha256
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/"experiments/analysis/v06/refinement_train_audit_v06_002.json"
EXPECTED="a3f8e33667c43e83a9f3199ea2f95fb8be0a7e29c968c017bfde8749aa1b5b34"
STYLE={"witness":("#71559C","o","-","Witness"),
    "relations":("#176B9B","s","--","Relations"),
    "objective":("#687782","^",":","Objective")}


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


if __name__=="__main__":
    assert digest(AUDIT)==EXPECTED
    audit=json.loads(AUDIT.read_bytes())
    assert audit["error_count"]==0 and audit["raw_slot_count"]==120
    rows=audit["candidate_summaries"]
    assert len(rows)==120 and len({r["id"] for r in rows})==120
    font_manager.findfont("Arial",fallback_to_default=False)
    plt.rcParams.update({"font.family":"Arial","font.size":9,"axes.labelsize":9,
        "xtick.labelsize":9,"ytick.labelsize":9,"legend.fontsize":8.5,
        "pdf.fonttype":42,"ps.fonttype":42,"axes.spines.top":False,
        "axes.spines.right":False,"axes.edgecolor":"#687782","axes.labelcolor":"#243640",
        "text.color":"#243640","xtick.color":"#243640","ytick.color":"#243640",
        "figure.facecolor":"white","savefig.facecolor":"white"})
    fig=plt.figure(figsize=(3.35,1.94)); ax=fig.add_axes([.155,.24,.82,.58])
    curves={}; handles=[]; x=np.arange(9)
    for arm,(color,marker,ls,label) in STYLE.items():
        blocks=[]
        for block in range(5):
            bank=sorted((r for r in rows if r["arm"]==arm and r["block"]==block),key=lambda r:r["slot"])
            assert [r["slot"] for r in bank]==list(range(8))
            values=np.r_[0,np.cumsum([int(r["eligible"]) for r in bank])]
            blocks.append(values)
            # The fifth, preregistered retained block remains visibly present.
            line,=ax.plot(x,values,color=color,lw=.6,alpha=.23,
                ls="--" if block==4 else "-")
            np.testing.assert_array_equal(line.get_ydata(),values)
        blocks=np.asarray(blocks); mean=blocks.mean(axis=0)
        line,=ax.plot(x,mean,color=color,lw=1.5,ls=ls,marker=marker,ms=3.3,label=label,zorder=4)
        np.testing.assert_array_equal(line.get_ydata(),mean)
        handles.append(line); curves[arm]={"all5_original_banks":blocks.tolist(),"all5_mean":mean.tolist(),
            "matched4_final_counts":blocks[:4,-1].tolist(),"retained5th_final_count":int(blocks[4,-1])}
    assert curves["witness"]["all5_mean"][-1]==5.6
    assert curves["relations"]["all5_mean"][-1]==4.8
    assert curves["objective"]["all5_mean"][-1]==0
    ax.set(xlim=(-.15,8.15),ylim=(-.15,8.35),xticks=[0,2,4,6,8],yticks=[0,2,4,6,8],
        xlabel="Original proposal positions",ylabel="Eligible proposals")
    ax.grid(axis="y",alpha=.15,lw=.5); ax.tick_params(length=3,pad=2)
    ax.xaxis.labelpad=3; ax.yaxis.labelpad=3
    fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.56,1.005),
        ncol=3,frameon=False,handlelength=1.25,handletextpad=.3,columnspacing=.65)
    outputs={}
    for ext in ("pdf","png"):
        path=ROOT/f"paper/figures/refinement_yield_v06.{ext}"
        fig.savefig(path,dpi=300); outputs[path.relative_to(ROOT).as_posix()]=digest(path)
    plt.close(fig)
    report={"version":"v06_R2_full5_information_yield_panel_001","audit_sha256":EXPECTED,
        "script_sha256":digest(__file__),"output_sha256":outputs,"curves":curves,
        "scope":"All5 fixed warm-refinement blocks; all40 positions per arm, no favorable block deletion",
        "semantics":"Thick=all5mean;thin=originalbanks;dashedthin=retainedfifth. Original slots are not learning iterations.",
        "font":"Arial9pt at native3.35in","TRAIN_only":True,"TEST_accessed":False,
        "selection_or_evaluation_or_inference":False}
    dest=ROOT/"experiments/analysis/v06/refinement_yield_panel_v06_001.json"
    dest.write_bytes((json.dumps(report,indent=2,allow_nan=False)+"\n").encode())
    print(json.dumps({"panel":str(path.with_suffix(".pdf")),"original_banks":15,"receipt_sha256":digest(dest)}))
