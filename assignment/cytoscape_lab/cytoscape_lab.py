"""Drive Cytoscape (CyREST, port 1234) + stringApp to run every step of the Cytoscape Guided Lab.

Cytoscape must be open with stringApp installed. Outputs go to assignment/cytoscape_lab/cytoscape_out/.
Run:  .venv/Scripts/python.exe assignment/cytoscape_lab/cytoscape_lab.py
"""
import json
import time
from pathlib import Path

import pandas as pd
import requests

R = "http://localhost:1234/v1"
OUT = (Path(__file__).parent / "cytoscape_out").resolve()
OUT.mkdir(exist_ok=True)

NETWORKS = [
    dict(key="Example1_TP53", query="TP53", species="Homo sapiens", limit=10),
    dict(key="Example2_Drought", species="Arabidopsis thaliana", limit=10,
         query="\n".join(["NCED3", "PYR1", "ABI1", "ABI2", "HAB1", "OST1",
                          "ABF2", "ABI5", "DREB2A", "RD29A"])),
    dict(key="Exercise_TB", query="\n".join(["TLR2", "VDR", "IFNG"]),
         species="Homo sapiens", limit=20),
]


def cmd(path, **args):
    r = requests.post(f"{R}/commands/{path}", json=args, timeout=600)
    r.raise_for_status()
    j = r.json()
    if j.get("errors"):
        raise RuntimeError(f"{path}: {j['errors']}")
    return j.get("data")


def rows(suid, table):
    return pd.DataFrame(requests.get(f"{R}/networks/{suid}/tables/{table}/rows").json())


def export_view(suid, name):
    cmd("view/fit content")
    view = requests.get(f"{R}/networks/{suid}/views").json()[0]
    img = requests.get(f"{R}/networks/{suid}/views/{view}.png", params={"h": 1600})
    img.raise_for_status()
    (OUT / f"{name}.png").write_bytes(img.content)


def style_hubs(suid):
    view = requests.get(f"{R}/networks/{suid}/views").json()[0]
    style = requests.get(f"{R}/networks/{suid}/views/{view}/currentStyle").json()["title"]
    nt = rows(suid, "defaultnode")
    dmin, dmax = int(nt.Degree.min()), int(nt.Degree.max())
    bmax = float(nt.BetweennessCentrality.max()) or 1e-6
    for vp in ("NODE_SIZE", "NODE_FILL_COLOR", "NODE_WIDTH", "NODE_HEIGHT", "NODE_CUSTOMGRAPHICS_1"):
        requests.delete(f"{R}/styles/{style}/mappings/{vp}")
    requests.put(f"{R}/styles/{style}/dependencies",
                 json=[{"visualPropertyDependency": "nodeSizeLocked", "enabled": True}])
    mappings = [
        {"mappingType": "continuous", "mappingColumn": "Degree", "mappingColumnType": "Integer",
         "visualProperty": "NODE_SIZE",
         "points": [{"value": dmin, "lesser": "20", "equal": "20", "greater": "20"},
                    {"value": max(dmax, dmin + 1), "lesser": "60", "equal": "60", "greater": "60"}]},
        {"mappingType": "continuous", "mappingColumn": "BetweennessCentrality",
         "mappingColumnType": "Double", "visualProperty": "NODE_FILL_COLOR",
         "points": [{"value": 0.0, "lesser": "#FFF5C0", "equal": "#FFF5C0", "greater": "#FFF5C0"},
                    {"value": bmax / 2, "lesser": "#FD8D3C", "equal": "#FD8D3C", "greater": "#FD8D3C"},
                    {"value": bmax, "lesser": "#B10026", "equal": "#B10026", "greater": "#B10026"}]},
    ]
    r = requests.post(f"{R}/styles/{style}/mappings", json=mappings)
    r.raise_for_status()
    requests.get(f"{R}/apply/styles/{style}/{suid}")


def run(key, query, species, limit):
    print(f"\n=== {key} ===")
    for attempt in range(5):  # the STRING server occasionally returns nothing; retry
        try:
            suid = cmd("string/protein query", query=query, species=species, limit=str(limit),
                       cutoff="0.4", newNetName=key, showGlassBallEffect="false",
                       showStructureImages="false")["SUID"]
            break
        except requests.HTTPError:
            if attempt == 4:
                raise
            time.sleep(20)
    time.sleep(2)
    export_view(suid, f"{key}_1_imported")

    stats = cmd("analyzer/analyze", directed="false", network=f"SUID:{suid}")
    style_hubs(suid)
    # = Layout -> Prefuse Force Directed Layout (longer springs so big hub nodes don't overlap)
    cmd("layout/force-directed", network=f"SUID:{suid}", defaultSpringLength="180",
        defaultNodeMass="5")
    time.sleep(1)
    export_view(suid, f"{key}_2_styled_hubs")

    before = set(cmd("table/list", type="unassigned")["tables"])
    cmd("string/retrieve enrichment")
    cmd("string/show enrichment")
    new = set(cmd("table/list", type="unassigned")["tables"]) - before

    nt = rows(suid, "defaultnode")
    nt = nt[["display name", "query term", "Degree", "BetweennessCentrality",
             "ClosenessCentrality", "stringdb::canonical name", "stringdb::description"]] \
        .sort_values(["Degree", "BetweennessCentrality"], ascending=False)
    nt.to_csv(OUT / f"{key}_node_table.csv", index=False)

    et = rows(suid, "defaultedge")
    names = dict(zip(rows(suid, "defaultnode")["name"], rows(suid, "defaultnode")["display name"]))
    et["edge"] = et["name"].map(lambda s: " - ".join(names.get(p.strip(), p) for p in s.split("(pp)")))
    ev = ["stringdb::experiments", "stringdb::databases", "stringdb::textmining",
          "stringdb::coexpression", "stringdb::neighborhood", "stringdb::fusion",
          "stringdb::cooccurrence"]
    ev = [c for c in ev if c in et.columns]
    et["strongest evidence"] = et[ev].fillna(0).idxmax(axis=1).str.replace("stringdb::", "")
    et = et[["edge", "stringdb::score", *ev, "strongest evidence"]].sort_values("stringdb::score", ascending=False)
    et.to_csv(OUT / f"{key}_edge_table.csv", index=False)

    enr_file = OUT / f"{key}_enrichment.csv"
    for t in new:  # stringApp creates a settings table too; keep the one with the terms
        tmp = OUT / f"_table_{t}.csv"
        cmd("table/export", table=f"SUID:{t}", options="CSV", outputFile=tmp.as_posix())
        d = pd.read_csv(tmp)
        tmp.unlink()
        if "FDR value" in d.columns:
            d.sort_values("FDR value").to_csv(enr_file, index=False)
    stats = {k: stats[k] for k in ("nodeCount", "edgeCount", "density", "avNeighbors")}
    print(stats)
    return dict(suid=suid, **stats)


if __name__ == "__main__":
    cmd("session/new")
    summary = {n["key"]: run(**n) for n in NETWORKS}
    cmd("session/save as", file=(OUT / "Cytoscape_Lab_134976.cys").as_posix())
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
