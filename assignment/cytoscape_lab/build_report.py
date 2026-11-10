"""Build the Word submission for the Cytoscape Guided Lab from the Cytoscape outputs.

Run after cytoscape_lab.py:  .venv/Scripts/python.exe assignment/cytoscape_lab/build_report.py
"""
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Inches, Pt

HERE = Path(__file__).parent
OUT = HERE / "cytoscape_out"
DOCX = HERE.parent / "Cytoscape Guided Lab (134976).docx"

nodes = {k: pd.read_csv(OUT / f"{k}_node_table.csv") for k in
         ("Example1_TP53", "Example2_Drought", "Exercise_TB")}
enr = {k: pd.read_csv(OUT / f"{k}_enrichment.csv") for k in nodes}

doc = Document()
doc.styles["Normal"].font.name = "Calibri"
doc.styles["Normal"].font.size = Pt(11)


def p(text="", bold_prefix=None):
    para = doc.add_paragraph()
    if bold_prefix:
        para.add_run(bold_prefix).bold = True
    para.add_run(text)
    return para


def figure(png, caption, width=6.2):
    doc.add_picture(str(OUT / png), width=Inches(width))
    c = doc.add_paragraph(caption)
    c.runs[0].italic = True


def placeholder(text):
    run = doc.add_paragraph().add_run(f"[INSERT SCREENSHOT: {text}]")
    run.bold = True
    run.font.highlight_color = WD_COLOR_INDEX.YELLOW


def table(df, widths=None):
    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = "Light Grid Accent 1"
    for i, c in enumerate(df.columns):
        t.rows[0].cells[i].text = str(c)
    for _, r in df.iterrows():
        cells = t.add_row().cells
        for i, v in enumerate(r):
            cells[i].text = f"{v:.4f}" if isinstance(v, float) else str(v)
    doc.add_paragraph()


def node_table(key, n=None):
    d = nodes[key][["display name", "query term", "Degree", "BetweennessCentrality",
                    "ClosenessCentrality"]].copy()
    d["query term"] = d["query term"].fillna("(added by STRING)")
    d.columns = ["Protein", "Query term", "Degree", "Betweenness", "Closeness"]
    table(d.head(n) if n else d)


def go_table(key, n):
    d = enr[key]
    d = d[d.category == "GO Biological Process"].head(n)
    d = d[["term name", "description", "# genes", "FDR value"]].copy()
    d["FDR value"] = d["FDR value"].map(lambda x: f"{x:.2e}")
    table(d)


# ---------------------------------------------------------------- title
doc.add_heading("Biological Network Analysis with Cytoscape", 0)
p("134976 Emmanuel Kipngetich Keter", "Name: ")
p("Computing for Bioinformatics – Cytoscape Guided Lab", "Course: ")
p("Cytoscape 3.10.5 with stringApp 2.2.0; STRING confidence cutoff 0.4; networks analysed "
  "as undirected with Tools → Analyze Network.", "Software: ")

# ---------------------------------------------------------------- Example 1
doc.add_heading("Example 1: A Human Cancer Network (TP53)", 1)
p("Query: TP53, species Homo sapiens, 10 additional interactors, confidence 0.4.")
figure("Example1_TP53_1_imported.png", "Figure 1. TP53 network as imported from STRING into Cytoscape.")
placeholder("Example 1 Node Table sorted by Degree (highest first)")
p("Node Table after Analyze Network (sorted by Degree):")
node_table("Example1_TP53")

doc.add_heading("Answers", 2)
e1 = pd.read_csv(OUT / "Example1_TP53_edge_table.csv")
top = e1[e1["stringdb::score"] == e1["stringdb::score"].max()]
p("The network has 11 nodes and 35 edges (TP53 plus its 10 STRING partners).", "1. ")
p("TP53 has the highest degree (10). It is connected to every other protein in the network. "
  "This is expected because the network was built around TP53: STRING only added proteins that "
  "interact with TP53, so every added node is a TP53 partner by construction. Biologically, p53 is "
  "a master regulator that integrates DNA-damage, stress and cell-cycle signals, so many proteins "
  "regulate it or are regulated by it. It is also one of the most studied human proteins, which "
  "adds more evidence (edges). TP53 also has the highest betweenness (0.19) and a closeness of 1.0.",
  "2. ")
p("", "3. ")
for name, txt in [
    ("MDM2", "an E3 ubiquitin ligase that tags p53 for destruction by the proteasome, keeping p53 "
             "levels low in healthy cells (the main 'off switch' for p53)."),
    ("ATM", "a serine/threonine kinase that senses DNA double-strand breaks and phosphorylates p53, "
            "switching on the cell-cycle checkpoint."),
    ("EP300", "a histone acetyltransferase that acetylates histones and p53 itself, helping p53 "
              "switch on its target genes."),
]:
    para = doc.add_paragraph(style="List Bullet")
    para.add_run(f"{name}: ").bold = True
    para.add_run(txt)
p(f"{len(top)} edges share the highest combined score of {top['stringdb::score'].max():.3f}: "
  + ", ".join(top["edge"]) + ". The strongest-supported of these is TP53–MDM2: its experimental "
  "score (0.999), curated database score (0.90) and text-mining score (0.999) are all near maximum.",
  "4. ")
p("Edge evidence (Step 6): for TP53 edges, the strongest evidence channels are experiments and text "
  "mining, with curated databases also high (e.g. TP53–RPA1: experiments 0.982, text mining 0.932). "
  "Neighbourhood, gene fusion and co-occurrence contribute nothing for these human edges.",
  "Note: ")

# ---------------------------------------------------------------- Example 2
doc.add_heading("Example 2: A Plant Drought-Response Network", 1)
p("Query: NCED3, PYR1, ABI1, ABI2, HAB1, OST1, ABF2, ABI5, DREB2A, RD29A; species Arabidopsis "
  "thaliana; 10 additional interactors; confidence 0.4. STRING resolved OST1 to its systematic "
  "name SRK2E. The network has 20 nodes and 134 edges (density 0.71).")
figure("Example2_Drought_1_imported.png", "Figure 2. ABA drought network as imported from STRING.")
figure("Example2_Drought_2_styled_hubs.png",
       "Figure 3. Styled network: node size = Degree, fill colour = BetweennessCentrality "
       "(pale yellow = low, dark red = high), Prefuse Force Directed layout.")
placeholder("Example 2 top rows of the STRING Enrichment table")
p("Node Table after Analyze Network (sorted by Degree):")
node_table("Example2_Drought")
p("Top enriched GO Biological Processes:")
go_table("Example2_Drought", 5)

doc.add_heading("Answers", 2)
p("Top 5 by Degree: ABI2 (19), SRK2E/OST1 (19), HAB1 (18), ABI1 (18), ABI5 (18). "
  "Top 5 by BetweennessCentrality: ABI2 (0.0528), SRK2E/OST1 (0.0528), HAB1 (0.0524), "
  "ABI1 (0.0524), ABI5 (0.0308). The two lists contain the same five proteins. The network is very "
  "dense (each protein has 13.4 partners on average), so almost every protein is linked directly. "
  "Betweenness values are therefore small, and they follow degree closely.", "1. ")
p("Yes. ABI2 has degree 19 (connected to every other node), while ABI1 and HAB1 have degree 18. "
  "Three of the four highest-degree proteins are brakes. These are PP2C phosphatases at the centre "
  "of ABA signalling. ABA-bound PYR/PYL receptors bind and inhibit them, and they in turn hold the "
  "OST1 kinase off. STRING added nine PYL receptors and ABF3, and these partners all interact with "
  "the PP2Cs, which raises the brakes' degree further.", "2. ")
p("Abscisic acid-activated signalling pathway (GO:0009738, 17 genes, FDR 3.9e-29) and response to "
  "abscisic acid (GO:0009737, 18 genes, FDR 6.9e-26); also regulation of protein serine/threonine "
  "phosphatase activity (FDR 4.5e-23) and the KEGG pathway Plant hormone signal transduction "
  "(FDR 5.9e-29). These make sense: ABA is the drought alarm hormone. The network contains the "
  "full chain from ABA synthesis (NCED3) to receptors (PYR/PYL) and phosphatase brakes (PP2Cs), "
  "then the kinase (OST1), transcription factors (ABF2/3, ABI5, DREB2A) and a protective output "
  "gene (RD29A).", "3. ")
p("I would study OST1 (SRK2E) first. It is tied for the highest degree (19) and the highest "
  "betweenness (0.053), so it is both a hub and a bottleneck. Unlike the PP2C brakes, it is a "
  "positive regulator: it directly triggers stomatal closure and phosphorylates the ABF/AREB "
  "transcription factors that switch on protective genes such as RD29A. Every signal from the "
  "receptors and brakes passes through it on the way to water saving. A breeder at KALRO could "
  "look for maize SnRK2 homologues of OST1 and select alleles or expression levels that close "
  "stomata faster under drought. Weakening a PP2C brake is an alternative strategy.", "4. ")

# ---------------------------------------------------------------- Exercise
doc.add_heading("Exercise: Tuberculosis – Host Immune Response", 1)
p("Chosen option: Tuberculosis (host immune response), species Homo sapiens. TB remains one of the "
  "leading infectious causes of death in Kenya. Starting genes TLR2, VDR, IFNG with 20 additional "
  "interactors at confidence 0.4. The final network has 23 nodes and 93 edges (density 0.37), and "
  "Analyze Network was run on this final network.")
p("STRING (v12.5, used by stringApp) has no entry for the vitamin D receptor under the name VDR. "
  "The query term VDR was resolved to CYP27B1 (25-hydroxyvitamin D 1-alpha-hydroxylase), the enzyme "
  "that makes active vitamin D inside macrophages. CYP27B1 belongs to the same vitamin D "
  "antimicrobial pathway, so it was kept and is discussed as a limitation below.", "Note on species/name check: ")
figure("Exercise_TB_2_styled_hubs.png",
       "Figure 4. Final TB host-response network: node size = Degree, fill colour = "
       "BetweennessCentrality, Prefuse Force Directed layout.")
placeholder("Exercise Node Table sorted by Degree (highest first)")
placeholder("Exercise STRING Enrichment results table")

doc.add_heading("Top 5 hubs", 2)
tb = nodes["Exercise_TB"]
hubs = tb.head(5)[["display name", "Degree", "BetweennessCentrality"]].copy()
hubs.insert(0, "Rank", range(1, 6))
hubs.columns = ["Rank", "Protein", "Degree", "Betweenness"]
table(hubs)
bc = tb.nlargest(5, "BetweennessCentrality")
p("Top 5 by BetweennessCentrality: " + ", ".join(
    f"{r['display name']} ({r.BetweennessCentrality:.3f})" for _, r in bc.iterrows())
  + ". These are the same five proteins as the degree hubs, in the same order.")

doc.add_heading("Three most significant biological processes / pathways", 2)
go_table("Exercise_TB", 3)
kegg = enr["Exercise_TB"]
kegg = kegg[kegg.category == "KEGG Pathways"].iloc[0]
p(f"The top KEGG pathway is {kegg['description']} ({kegg['term name']}, {kegg['# genes']} genes, "
  f"FDR {kegg['FDR value']:.1e}). STRING recovered the TB pathway itself from just three seed genes.")

doc.add_heading("Interpretation and limitation", 2)
doc.add_paragraph(
    "The top hub, TLR2 (degree 22, betweenness 0.27), makes strong biological sense for "
    "tuberculosis. TLR2 is the main pattern-recognition receptor that detects Mycobacterium "
    "tuberculosis lipoproteins and lipoarabinomannan on macrophages. It works as a heterodimer with "
    "TLR1 (rank 3) or TLR6 and signals through TIRAP to switch on inflammatory cytokines. TLR2/1 "
    "signalling also induces CYP27B1 and the vitamin D receptor. Active vitamin D then switches on "
    "the antimicrobial peptides cathelicidin (CAMP, rank 5) and beta-defensin 2 (DEFB4A), all of "
    "which appear in this network. The second hub, IFNG (degree 21), is the Th1 cytokine that "
    "activates macrophages to kill intracellular mycobacteria. People with defects in the "
    "IFN-gamma pathway are highly susceptible to mycobacterial disease. Together the hubs reproduce "
    "the innate-recognition and macrophage-activation axis of TB immunity. One limitation is that "
    "the network depends on STRING's names and evidence: VDR could not be found and was silently "
    "replaced by CYP27B1, so the vitamin D receptor itself is missing. Also, TLR2 and IFNG are hubs "
    "partly by construction, because the 20 added proteins were chosen as their partners. Many edges "
    "come mainly from text mining, which favours well-studied proteins, so the network shows "
    "evidence of association rather than proven physical interactions during infection.")

# ---------------------------------------------------------------- Reflection
doc.add_heading("Reflection", 1)
doc.add_paragraph(
    "This lab showed me how to turn a list of genes into an interaction network and read its "
    "structure. Degree identifies hubs, betweenness identifies bridges, and functional enrichment "
    "tells you what a module does. In all three networks the hubs were biologically meaningful: "
    "TP53 in DNA damage, the PP2C brakes and OST1 in ABA signalling, and TLR2 and IFNG in TB "
    "immunity. I also learnt to treat STRING edges as evidence with a confidence score, not as "
    "facts, and to check how each name is resolved. OST1 came back as SRK2E, and VDR was "
    "mismapped to CYP27B1, which would have been easy to miss without checking the species and "
    "query terms. The challenging parts were interpreting betweenness in a very dense network "
    "(Example 2), where almost every node touches every other node so the values become small and "
    "track degree. Another challenge was remembering that query genes become hubs partly by "
    "construction. Cytoscape also needs a stable internet connection because STRING data is "
    "downloaded live.")

doc.save(DOCX)
print("saved", DOCX)
