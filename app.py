import io, pickle, random, itertools, json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from os import PathLike
import pandas as pd
import streamlit as st
from typing import List, Tuple
from pathlib import Path
import json, pickle
import re
import textwrap

st.set_page_config(page_title="Ranking Study", page_icon="🩺", layout="wide")

def _map_level(val, mapping: dict, fallback: str = "unknown") -> str:
    return mapping.get(val, fallback)

# 1) Add these small helpers and rules near your function (or at top of the file)
ABNORMAL_RULES = {
    "risk_band": {"medium": "orange", "high": "red"},
    "smoker": {"yes": "red"},
    "ses": {"low": "red"},
    "adherence": {"low": "red"},
    # BMI handled by thresholds below
}

def _colorize(val: str, color: str | None) -> str:
    return f'<span class="val {color}">{val}</span>' if color else val

def _abnormal_color(name: str, value_str: str, value_num: float | None = None) -> str | None:
    """
    Returns a color name if abnormal, else None.
    name: one of {'risk_band','smoker','ses','adherence','bmi'}
    value_str: normalized, lowercase string label of the value to check
    value_num: numeric value for thresholded checks (e.g., BMI)
    """
    if name == "bmi":
        if value_num is None:
            return None
        if value_num >= 30:
            return "red"
        if value_num >= 25:
            return "orange"
        return None

    rules = ABNORMAL_RULES.get(name, {})
    return rules.get(value_str)  # returns color or None

# def patient_card_html(label: str, p: dict, selected: bool, side: str,
#                       category_order: list[str] | None = None,
#                       per_category_master: dict[str, list[str]] | None = None) -> str:
#     sex_label       = "male" if int(p["sex"]) == 1 else "female"
#     smoker_label    = "yes" if int(p["smoker"]) == 1 else "no"
#     diabetes_label  = "yes" if int(p["diabetes"]) == 1 else "no"
#     ses_label       = _map_level(int(p["socio_economic"]), {1: "low", 2: "medium", 3: "high"})
#     risk_band_label = _map_level(int(p.get("risk_band", 0)), {1: "low", 2: "medium", 3: "high"})
#     adherence_val   = str(p.get("adherence", "none"))
#     adherence_lab   = "not applicable (no chronic meds)" if adherence_val == "none" else adherence_val
#     bmi_val         = float(p["bmi"])
#     sel_class       = " selected" if selected else ""
#     recs_html = recs_grouped_html_for_patient(
#         p, category_order=category_order, per_category_master=per_category_master
#     )
#     abnornal_values = {risk_band_label: {"medium": "orange", "high": "red"}, smoker_label: {"yes": "red"}, ses_label: {"low": "red"}, adherence_lab: {"low": "red", "medium": "orange"}, bmi_val: {30: "red", 25: "orange"}}


#     html = f"""
# <div class="frame {side}{sel_class}"></div>

# <div class="card-badge cell badge {side}">{label}</div>

# <div class="section cell sec-demo {side}">
#   <div class="section-title">Demographics</div>
#   <div class="row row-3">
#     <div><span class="item-label">Age:</span> {int(p['age'])}</div>
#     <div><span class="item-label">Sex:</span> {sex_label}</div>
#     <div><span class="item-label">Socio-economic:</span> {ses_label}</div>
#   </div>
# </div>

# <div class="section cell sec-risk {side}">
#   <div class="section-title">Predicted Risk</div>
#   <div class="row row-2 rm-top">
#     <div><span class="item-label-2"><span class="item-label">SCORE2</span>(10-year CVD risk):</span> {int(p['risk'])}%</div>
#     <div><span class="item-label">Risk band for age:</span> {risk_band_label}</div>
#   </div>
# </div>

# <div class="section cell sec-mods {side}">
#   <div class="section-title">Modifiable Behavior</div>
#   <div class="row row-3">
#     <div><span class="item-label">BMI:</span> {int(round(bmi_val))}</div>
#     <div><span class="item-label">Smoker:</span> {smoker_label}</div>
#     <div><span class="item-label">Adherence:</span> {adherence_lab}</div>

#   </div>
# </div>


# <div class="section section-recs cell sec-recs {side}">
#   <div class="section-title">C-Pi recommendations</div>
#   <ul class="recs">{recs_html}</ul>
# </div>
# """
#     return textwrap.dedent(html).strip()

# 2) Update your patient_card_html to colorize the displayed values
def patient_card_html(label: str, p: dict, selected: bool, side: str,
                      category_order: list[str] | None = None,
                      per_category_master: dict[str, list[str]] | None = None) -> str:
    sex_label       = "male" if int(p["sex"]) == 1 else "female"
    smoker_label    = "yes" if int(p["smoker"]) == 1 else "no"
    diabetes_label  = "yes" if int(p["diabetes"]) == 1 else "no"
    ses_label       = _map_level(int(p["socio_economic"]), {1: "low", 2: "medium", 3: "high"})
    risk_band_label = _map_level(int(p.get("risk_band", 0)), {1: "low", 2: "medium", 3: "high"})
    adherence_val   = str(p.get("adherence", "none"))
    adherence_lab   = "not applicable (no chronic meds)" if adherence_val == "none" else adherence_val
    bmi_val         = float(p["bmi"])
    sel_class       = " selected" if selected else ""
    recs_html = recs_grouped_html_for_patient(
        p, category_order=category_order, per_category_master=per_category_master
    )

    # --- colorized display strings ---
    risk_band_disp = _colorize(risk_band_label, _abnormal_color("risk_band", risk_band_label))
    smoker_disp    = _colorize(smoker_label,     _abnormal_color("smoker", smoker_label))
    ses_disp       = _colorize(ses_label,        _abnormal_color("ses", ses_label))
    # only color adherence if it's one of the graded labels (not the 'not applicable...' string)
    adherence_disp = ( _colorize(adherence_lab, _abnormal_color("adherence", adherence_lab))
                       if adherence_val != "none" else adherence_lab )
    bmi_disp = _colorize(f"{bmi_val:.1f}", _abnormal_color("bmi", "", bmi_val))

    html = f"""
<div class="frame {side}{sel_class}"></div>

<div class="card-badge cell badge {side}">{label}</div>

<div class="section cell sec-demo {side}">
  <div class="section-title">Demographics</div>  
  <div class="row row-3">
    <div><span class="item-label">Age:</span> {int(p['age'])}</div>
    <div><span class="item-label">Sex:</span> {sex_label}</div>
    <div><span class="item-label">Socio-economic:</span> {ses_disp}</div>
  </div>
</div>

<div class="section cell sec-risk {side}">
  <div class="section-title">Predicted Risk</div>
  <div class="row row-2 rm-top">
<div><span class="item-label-2"><span class="item-label">SCORE2</span>(10-year CVD risk):</span>
  <span class="risk-pct">{int(p['risk'])}%</span>
</div>
    <div><span class="item-label">Risk band for age:</span> {risk_band_disp}</div>
  </div>
</div>

<div class="section cell sec-mods {side}">
  <div class="section-title">Modifiable Behavior</div>
  <div class="row row-3">
    <div><span class="item-label">BMI:</span> {bmi_disp}</div>
    <div><span class="item-label">Smoker:</span> {smoker_disp}</div>
    <div><span class="item-label">Adherence:</span> {adherence_disp}</div>
  </div>
</div>

<div class="section section-recs cell sec-recs {side}">
  <div class="section-title">C-Pi recommendations</div>
  <ul class="recs">{recs_html}</ul>
</div>
"""
    return textwrap.dedent(html).strip()

st.markdown("""
<style>
:root{
  --page-bg:#ffffff; --page-fg:#111111;
  --card-bg:#ffffff; --card-fg:#1f1f1f;
  --card-border:#d7d7d7; --inset-divider:#dfdfdf;
  --card-shadow:0 2px 6px rgba(0,0,0,.06);
  --card-selected-bg:#f7fcf7; --card-selected-border:#34c759;
}
@media (prefers-color-scheme: dark){
  :root{
    --page-bg:#0e0f12; --page-fg:#eaeaea;
    --card-bg:#17181c; --card-fg:#e7e7e7;
    --card-border:#2b2f36; --inset-divider:#2f333a;
    --card-shadow:0 4px 14px rgba(0,0,0,.6);
    --card-selected-bg:#132a1b; --card-selected-border:#2ecc71;
  }
}
html, body{ background:var(--page-bg); color:var(--page-fg); }

/* Two-column parent grid (shared row tracks) */
.pair-grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  column-gap:16px;
  grid-template-areas:
    "badgeL badgeR"
    "demoL  demoR"
    "riskL  riskR"
    "modsL  modsR"
    "adhL   adhR"
    "recsL  recsR";
  align-items:stretch;
  color:var(--card-fg);
}

/* Sections placed directly into the grid */
.cell{ z-index:1; }
.badge.left  { grid-area:badgeL; }
.badge.right { grid-area:badgeR; }
.sec-demo.left  { grid-area:demoL; }
.sec-demo.right { grid-area:demoR; }
.sec-risk.left  { grid-area:riskL; }
.sec-risk.right { grid-area:riskR; }
.sec-mods.left  { grid-area:modsL; }
.sec-mods.right { grid-area:modsR; }
.sec-adh.left   { grid-area:adhL; }
.sec-adh.right  { grid-area:adhR; }
.sec-recs.left  { grid-area:recsL; }
.sec-recs.right { grid-area:recsR; }

/* The background/border frame spans all rows in its column */
.frame{
  grid-row:1 / -1;
  position:relative;
  z-index:0;
  background:var(--card-bg);
  border:3px solid var(--card-border);
  border-radius:14px;
  box-shadow:var(--card-shadow);
}
.frame.left  { grid-column:1; }
.frame.right { grid-column:2; }
.frame.selected{ background:var(--card-selected-bg); border-color:var(--card-selected-border); }

/* Section + rows styling */
.card-badge{font-weight:700;font-size:.95rem;padding:10px 14px;border-bottom:2px solid var(--inset-divider)}
.section{padding:10px 14px 12px;border-bottom:2px solid var(--inset-divider)}
.section:last-of-type{border-bottom:0}
.section-title{font-weight:800;margin-bottom:8px}
.row{display:grid}
.row-3{ grid-template-columns:1fr 1fr 1fr; }
.row-2{ grid-template-columns:1fr 1fr; }
.row-1{ grid-template-columns:1fr; }
.row>*{padding:4px 10px 4px 0}
.row>*:not(:first-child){border-left:2px solid var(--inset-divider);padding-left:12px}
.rm-top{ margin-bottom:10px; }

/* Recs */
ul.recs{margin:6px 0 0 1.1rem}
ul.recs li{margin:.2rem 0}
ul.recs li.ghost{opacity:.45;font-style:italic}
.recs .rec-cat{ text-decoration:underline; text-underline-offset:2px; text-decoration-thickness:2px; }
.recs .rec-main{ font-weight:700; }
.recs .rec-cost{ font-style:italic; }
.item-label{margin-right:6px; text-decoration:underline; text-underline-offset:2px; text-decoration-thickness:2px; }
.item-label-2{margin-right:6px}
.risk-pct{ font-weight: 700; }
     
.val {
  font-weight: 800;
  padding: 0 .25rem;
  border-radius: .35rem;
}
.val.red {
  color: #b00020;
}
.val.orange {
  color: #e67e22; /* lighter orange */
}  
/* (optional) subtle backgrounds for contrast – uncomment if you want chips */
/*
.val.red{ background:rgba(176,0,32,.12); }
.val.orange{ background:rgba(192,86,0,.12); }
color: #e67e22; /* lighter orange */
            
/* Make left & middle a bit narrower; right column broader */
.sec-demo .row-3,
.sec-mods .row-3{
  grid-template-columns: 0.75fr 0.75fr 1.5fr;
}

/* (optional) on narrow screens, fall back to equal columns or a stack */
@media (max-width: 900px){
  .sec-demo .row-3,
  .sec-mods .row-3{
    grid-template-columns: 1fr 1fr 1fr; /* or: 1fr to stack */
  }
}

}
/* compact spacing inside cells */
.pair-grid .card-badge{
  padding: 8px 10px;
}
.pair-grid .section{
  padding: 6px 10px 8px;   /* was 10px 14px 12px */
}
.pair-grid .section-title{
  margin-bottom: 6px;      /* was 8px */
}
.pair-grid .row > *{
  padding: 2px 6px 2px 0;  /* was 4px 10px 4px 0 */
  line-height: 1.25;       /* slightly tighter */
}
/* keep the divider but reduce left padding for middle/right cells */
.pair-grid .row > *:not(:first-child){
  padding-left: 8px;       /* was 12px */
}

/* optional: tighten recs list a bit */
.pair-grid ul.recs{ margin: 4px 0 0 1rem; }
.pair-grid ul.recs li{ margin: .15rem 0; }

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&display=swap');

/* Define font stacks so it's easy to switch later */
:root{
  --body-font: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji";
  --header-font: "Poppins", ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
}

/* Apply */
body, html{
  font-family: var(--body-font);
}
.card-badge,
.section-title{
  font-family: var(--header-font);
  letter-spacing: .2px;       /* tiny polish */
}

/* If you want headers a touch heavier without changing size */
.section-title{ font-weight: 700;  }
.card-badge{   font-weight: 700; }
            
            .card-badge,
.card-badge,
.section-title {
  color: #444444; /* darker gray */
}

@media (prefers-color-scheme: dark) {
  .card-badge,
  .section-title {
    color: #cccccc; /* balanced for dark mode */
  }
}
}
            
           
</style>
""", unsafe_allow_html=True)

PATIENT_DF_PATH = (Path(__file__).parent / "patient_df.csv").resolve()

_RAW_REC_MAP = {
    "rec1":  {"DL": "Labs - for risk stratification / screening: lipid panel (cost 2)", "category": "Labs", "main": "lipid panel", "cost": "(cost 2)"},
    "rec2":  {"DL": "Labs - for treatment monitoring: liver enzymes (cost 1)", "category": "Labs", "main": "liver enzymes", "cost": "(cost 1)"},
    "rec3":  {"DL": "Labs - for risk stratification / screening:  Lp(a) (cost 6)", "category": "Labs", "main": "Lp(a)", "cost": "(cost 6)"},
    "rec4":  {"DL": "Labs - for treatment monitoring: LDL (cost 2)",  "category": "Labs", "main": "LDL", "cost": "(cost 2)"},
    "rec5":  {"DL": "Imaging - for risk stratification: carotid doppler (cost 20)",  "category": "Imaging", "main": "carotid doppler", "cost": "(cost 20)"},
    "rec6":  {"DL": "Treatment - initiate first-line: low dose statin (yearly cost 200)", "category": "Treatment", "main": "low dose statin", "cost": "(yearly cost 200)"}, 
    "rec7":  {"DL": "Treatment - initiate advanced treatment: high dose statin (yearly cost 200)", "category": "Treatment", "main": "high dose statin", "cost": "(yearly cost 200)"}, 
    "rec8":  {"DL": "Treatment - prescribe advanced treatment: PCSK9 (yearly cost 20,000)", "category": "Treatment", "main": "PCSK9", "cost": "(yearly cost 20,000)"}, 
    "rec9":  {"DL": "Treatment - upgrade: high dose statin (yearly cost 200)", "category": "Treatment", "main": "high dose statin", "cost": "(yearly cost 200)"},  
    "rec10": {"DL": "Treatment - replacement d/t contraindication: switch to PCSK9 (yearly cost 20,000)",  "category": "Treatment", "main": "PCSK9", "cost": "(yearly cost 20,000)"}, 
    "rec11": {"DL": "Consults - lipidologist consult: d/t statins failure/intolerance, to consider PCSK9 (cost 6)", "category": "Consults", "main": "lipidologist", "cost": "(cost 6)"}, 
    "rec12": {"DL": "Consults - hepatology consult: d/t high liver enzymes after statin initiation (cost 5)", "category": "Consults", "main": "hepatology", "cost": "(cost 5)"}, 
    "rec13": {"DL": "Lifestyle - dietitian: package of nutritional consultation sessions (cost 20)",  "category": "Lifestyle", "main": "nutritional consultation", "cost": "(cost 20)"}, 
    "rec14": {"DL": "Treatment - discuss pros/cons of drugs vs. lifestyle changes in gray-zone patients (cost 2)",  "category": "Treatment", "main": "discuss pros/cons", "cost": "(cost 2)"}, 
    "rec15": {"DL": "Lifestyle - consult about exercise, nutrition, and smoking (cost 2)",  "category": "Lifestyle", "main": "exercise, nutrition, and smoking", "cost": "(cost 2)"},
    "rec16": {"DL": 'Lifestyle - reccomend the AHA "Heart & Stroke Helper" app to track lipids, meds and lifestyle (cost 0)',  "category": "Lifestyle", "main": '"Heart & Stroke Helper" app', "cost": "(cost 0)"}
}

# # old version
# _RAW_REC_MAP = {
#     "rec1":  {"DL": "Labs - for risk stratification / screening: lipid panel (cost 2)"},
#     "rec2":  {"DL": "Labs - for treatment monitoring: liver enzymes (cost 1)"},
#     "rec3":  {"DL": "Labs - for risk stratification / screening:  Lp(a) (cost 6)"},
#     "rec4":  {"DL": "Labs - for treatment monitoring: LDL (cost 2)"},
#     "rec5":  {"DL": "Imaging - for risk stratification: carotid doppler (cost 20)"},
#     "rec6":  {"DL": "Treatment - initiate first-line treatment: low dose statin (yearly cost 200)"},
#     "rec7":  {"DL": "Treatment - initiate advanced treatment: high dose statin (yearly cost 200)"},
#     "rec8":  {"DL": "Treatment - prescribe advanced treatment: PCSK9 (yearly cost 20,000)"},
#     "rec9":  {"DL": "Treatment - upgrade: switch to a high dose statin (yearly cost 200)"},
#     "rec10": {"DL": "Treatment - replacement d/t contraindication: switch to PCSK9 (yearly cost 20,000)"},
#     "rec11": {"DL": "Consults - lipidologist consult: d/t statins failure/intolerance, to consider PCSK9 (cost 6)"},
#     "rec12": {"DL": "Consults - hepatology consult: d/t high liver enzymes after statin initiation (cost 5)"},
#     "rec13": {"DL": "Lifestyle - dietitian: referral for a package of nutritional consultation sessions (cost 20)"},
#     "rec14": {"DL": "Treatment - discuss pros/cons of drug treatment vs. lifestyle changes in gray-zone patients (cost 2)"},
#     "rec15": {"DL": "Lifestyle - consult about exercise, nutrition, and smoking cessation (cost 2)"},
#     "rec16": {"DL": 'Lifestyle - reccomend the AHA "Heart & Stroke Helper" app to track lipids, meds and lifestyle (cost 0)'}
# }
# _CATEGORY_ORDER = ["Labs", "Imaging", "Treatment", "Consults", "Lifestyle", "Other"]

# def recs_grouped_html_for_patient(p: dict) -> str:
#     """
#     Returns HTML <li> items of FULL DL sentences, with:
#       - category in <span class="rec-cat">…</span>  (bold via CSS)
#       - main     in <span class="rec-main">…</span> (bold via CSS)
#       - cost     in <span class="rec-cost">…</span> (italic via CSS)
#     Grouped by _CATEGORY_ORDER; within a category preserves map order.
#     """
#     chosen = set(p.get("recommendations") or [])
#     if not chosen or chosen == {"no active recommendations"}:
#         return "<li>no active recommendations</li>"

#     # Collect chosen items with display metadata
#     items = []
#     for idx, (key, meta) in enumerate(_RAW_REC_MAP.items()):
#         dl = meta.get("DL", "")
#         if dl in chosen:
#             cat  = meta.get("category", "Other")
#             main = meta.get("main", "")
#             cost = meta.get("cost", "")
#             items.append((cat, idx, dl, main, cost))

#     if not items:
#         return "<li>no active recommendations</li>"

#     # Sort by category, then original order
#     order_index = {c: i for i, c in enumerate(_CATEGORY_ORDER)}
#     items.sort(key=lambda t: (order_index.get(t[0], 999), t[1]))

#     # Render full DL with targeted styling
#     def _style_dl(dl: str, cat: str, main: str, cost: str) -> str:
#         s = dl
#         # category at the start -> bold
#         s = re.sub(r'^' + re.escape(cat) + r'(?=\s*-\s*)',
#                    f'<span class="rec-cat">{cat}</span>', s, count=1)
#         # first occurrence of main -> bold
#         if main:
#             s = re.sub(re.escape(main),
#                        f'<span class="rec-main">{main}</span>', s, count=1)
#         # first occurrence of cost -> italic
#         if cost:
#             s = re.sub(re.escape(cost),
#                        f'<span class="rec-cost">{cost}</span>', s, count=1)
#         return s

#     parts, prev_cat = [], None
#     for cat, _, dl, main, cost in items:
#         cls = "cat-start" if cat != prev_cat else ""
#         parts.append(f'<li class="{cls}">{_style_dl(dl, cat, main, cost)}</li>')
#         prev_cat = cat
#     return "".join(parts)

_CATEGORY_ORDER = ["Labs", "Imaging", "Treatment", "Consults", "Lifestyle", "Other"]

def recs_grouped_html_for_patient(
    p: dict,
    category_order: list[str] | None = None,
    per_category_master: dict[str, list[str]] | None = None
) -> str:
    """
    Render FULL DL sentences with styled parts, aligned by a shared plan:
    - category_order: order of categories (common first)
    - per_category_master: for each category, the ordered list of DLs (common first,
      then the side-unique ones). Missing items are shown as light placeholders to
      preserve vertical alignment.
    """
    chosen = set(p.get("recommendations") or [])
    order = category_order or _CATEGORY_ORDER

    # quick index from DL -> meta
    dl2meta = {meta["DL"]: meta for meta in _RAW_REC_MAP.values()}

    def _style_dl(dl: str, cat: str, main: str, cost: str) -> str:
        s = dl
        s = re.sub(r'^' + re.escape(cat) + r'(?=\s*-\s*)',
                   f'<span class="rec-cat">{cat}</span>', s, count=1)
        if main:
            s = re.sub(re.escape(main), f'<span class="rec-main">{main}</span>', s, count=1)
        if cost:
            s = re.sub(re.escape(cost), f'<span class="rec-cost">{cost}</span>', s, count=1)
        return s

    parts = []
    # if we have a master plan: iterate exact rows; else fall back to simple grouping
    if per_category_master:
        for cat in order:
            dls = per_category_master.get(cat, [])
            first_in_cat = True
            for dl in dls:
                if dl in chosen:
                    meta = dl2meta.get(dl, {})
                    html = _style_dl(dl, cat, meta.get("main",""), meta.get("cost",""))
                    cls = "cat-start" if first_in_cat else ""
                    parts.append(f'<li class="{cls}">{html}</li>')
                else:
                    # placeholder row so identical recs align line-by-line
                    cls = "cat-start ghost" if first_in_cat else "ghost"
                    # parts.append(f'<li class="{cls}">—</li>')
                first_in_cat = False
        return "".join(parts)

    # (fallback — not used when we pass a plan)
    # flat, grouped by global order
    by_cat = {}
    for _, meta in _RAW_REC_MAP.items():
        dl = meta["DL"]
        if dl in chosen:
            by_cat.setdefault(meta["category"], []).append(dl)
    for cat in order:
        for dl in by_cat.get(cat, []):
            meta = dl2meta.get(dl, {})
            html = _style_dl(dl, cat, meta.get("main",""), meta.get("cost",""))
            parts.append(f'<li class="cat-start">{html}</li>')
    return "".join(parts) or "<li>no active recommendations</li>"

def recs_by_category_for_patient(p: dict) -> dict[str, list[str]]:
    chosen = set(p.get("recommendations") or [])
    out: dict[str, list[str]] = {}
    for _, meta in _RAW_REC_MAP.items():
        dl = meta["DL"]
        if dl in chosen:
            out.setdefault(meta["category"], []).append(dl)
    return out

def build_pair_recs_alignment_plan(pX: dict, pY: dict):
    by_x = recs_by_category_for_patient(pX)
    by_y = recs_by_category_for_patient(pY)

    cats_x, cats_y = set(by_x.keys()), set(by_y.keys())
    common = [c for c in _CATEGORY_ORDER if c in cats_x and c in cats_y]
    rest   = [c for c in _CATEGORY_ORDER if c not in common and (c in cats_x or c in cats_y)]
    category_order = common + rest

    # per-category master list: common DLs first (map order), then X-only, then Y-only
    per_cat: dict[str, list[str]] = {}
    for cat in category_order:
        xs = by_x.get(cat, [])
        ys = by_y.get(cat, [])
        commons = [dl for dl in xs if dl in ys]
        x_only  = [dl for dl in xs if dl not in commons]
        y_only  = [dl for dl in ys if dl not in commons]
        per_cat[cat] = commons + x_only + y_only
    return category_order, per_cat

# ─────────────────────────────────────────────────────────────────────────────
# Small helpers

@st.cache_data(show_spinner=False)
def load_patient_df_from_repo(path: Path | str | PathLike) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File A not found at: {path}")

    suf = path.suffix.lower()
    if suf == ".csv":
        df = pd.read_csv(path)
    elif suf == ".xlsx":
        # pip install openpyxl
        df = pd.read_excel(path, engine="openpyxl")
    elif suf == ".xls":
        # pip install xlrd==1.2.0  (or convert to .xlsx)
        df = pd.read_excel(path, engine="xlrd")
    elif suf in (".pkl", ".pickle"):
        df = pd.read_pickle(path)
    else:
        raise ValueError(f"Unsupported File A extension: {suf}")

    # Normalize & validate columns
    df.columns = [str(c) for c in df.columns]
    required = {"patient_num", "age", "risk", "sex", "adherence", "bmi", "diabetes", "smoker", "socio_economic"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"patient_df missing required columns: {missing}")

    rec_cols = [c for c in df.columns if c.startswith("rec")]
    # Ensure rec1..rec21 exist and are ints
    for i in range(1, len(rec_cols) + 1):
        col = f"rec{i}"
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].fillna(0).astype(int)

    df["patient_num"] = df["patient_num"].astype(int)
    df["age"] = df["age"].astype(int)
    df["risk"] = df["risk"].astype(int)
    df["sex"] = df["sex"].astype(int)
    df["bmi"] = df["bmi"].astype(float)
    df["adherence"] = df["adherence"].astype(str)
    df["diabetes"] = df["diabetes"].astype(int)
    df["smoker"] = df["smoker"].astype(int)
    df["socio_economic"] = df["socio_economic"].astype(int)
    return df

def _slugify(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9._-]+", "_", s)
    return s.strip("_")

def _compose_output_filename(upload_name: str, user_name: str | None) -> str:
    """
    Rules:
    - Start from the uploaded file's stem (ignore original extension).
    - If the stem doesn't already include the user name slug, prefix it.
    - Always end with `_ranked.json`.
    """
    stem = Path(upload_name).stem                     # e.g. "train_initial_100_pairs"
    user_slug = _slugify(user_name or "")
    stem_norm = _slugify(stem)

    # add user prefix if missing
    if user_slug and user_slug not in stem_norm:
        stem = f"{user_slug}_{stem}"

    # add `_ranked` if missing
    if not stem.lower().endswith("_ranked"):
        stem = f"{stem}_ranked"

    return f"{stem}.json"

def _rec_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if str(c).lower().startswith("rec")]

def recs_from_row(row_dict: dict) -> list[str]:
    out = []
    for key, meta in _RAW_REC_MAP.items():
        val = row_dict.get(key, 0)
        try:
            val = int(val)
        except Exception:
            pass
        if val:
            out.append(meta["DL"])
    return out or ["no active recommendations"]

def normalize_patient(row_dict: dict) -> dict:
    return {
        "id": int(row_dict.get("patient_num")),
        "age": int(row_dict.get("age")),
        "risk": int(row_dict.get("risk")),
        "risk_band": int(row_dict.get("risk_band")),
        "sex": int(row_dict.get("sex")), 
        "bmi": float(row_dict.get("bmi")), 
        "adherence": str(row_dict.get("adherence")), 
        "diabetes": int(row_dict.get("diabetes")), 
        "smoker": int(row_dict.get("smoker")), 
        "socio_economic": int(row_dict.get("socio_economic")), 
        "recommendations": recs_from_row(row_dict),
    }

def read_patient_df(file) -> pd.DataFrame:
    """
    Accept CSV, PKL, or Excel (.xlsx/.xls).
    Ensures required columns exist and fills any missing rec1..rec21 with zeros.
    """
    name = (getattr(file, "name", "") or "").lower()

    if name.endswith(".csv"):
        df = pd.read_csv(file)
    elif name.endswith(".xlsx"):
        try:
            df = pd.read_excel(file, engine="openpyxl")  # pip install openpyxl
        except Exception as e:
            raise RuntimeError(
                "Reading .xlsx requires the 'openpyxl' package. Try: pip install openpyxl"
            ) from e
    elif name.endswith(".xls"):
        # xlrd>=2.0.0 removed xls support; you need xlrd<=1.2.0 or convert to .xlsx
        try:
            df = pd.read_excel(file, engine="xlrd")  # pip install xlrd==1.2.0
        except Exception as e:
            raise RuntimeError(
                "Reading .xls requires 'xlrd==1.2.0'. Either install it or save the file as .xlsx."
            ) from e
    else:
        # assume a pickle of a pandas DataFrame
        df = pd.read_pickle(file)

    # Normalize column names to strings
    df.columns = [str(c) for c in df.columns]

    # Required columns
    required = {"patient_num", "age", "risk", "sex", "adherence", "bmi", "diabetes", "smoker", "socio_economic"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"patient_df missing required columns: {missing}")


    rec_cols = [c for c in df.columns if c.startswith("rec")]
    # Ensure rec1..rec21 exist and are ints
    for i in range(1, len(rec_cols) + 1):
        col = f"rec{i}"
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].fillna(0).astype(int)

    df["patient_num"] = df["patient_num"].astype(int)
    df["age"] = df["age"].astype(int)
    df["risk"] = df["risk"].astype(int)
    df["sex"] = df["sex"].astype(int)
    df["bmi"] = df["bmi"].astype(float)
    df["adherence"] = df["adherence"].astype(str)
    df["diabetes"] = df["diabetes"].astype(int)
    df["smoker"] = df["smoker"].astype(int)
    df["socio_economic"] = df["socio_economic"].astype(int)
    return df

def read_pairs_pkl(file) -> List[Tuple[int, int]]:
    """Reads a PKL that contains a list of 2-tuples of ints."""
    data = pickle.load(file)
    # basic sanity checks
    if not isinstance(data, (list, tuple)):
        raise ValueError("pairs_for_ranking must be a list/tuple of (a, b).")
    pairs = []
    for t in data:
        if not (isinstance(t, (list, tuple)) and len(t) == 2):
            raise ValueError(f"Invalid pair entry: {t}")
        a, b = int(t[0]), int(t[1])
        if a == b:
            continue
        pairs.append((a, b))
    if not pairs:
        raise ValueError("No valid pairs found.")
    return pairs


def read_pairs_file(file) -> List[Tuple[int, int]]:
    """
    Reads an uploaded file containing pairs:
      - .pkl : pickled list/tuple of 2-tuples/lists
      - .json: JSON list of [a, b] (or (a, b)) items
    Returns: list of (int, int)
    """
    if file is None:
        raise ValueError("No file provided.")

    # Try to detect by extension; default to PKL if unknown
    suffix = Path(getattr(file, "name", "")).suffix.lower()
    parse_as_json = (suffix == ".json")

    # Reset pointer (Streamlit uploader may have been read before)
    try:
        file.seek(0)
    except Exception:
        pass  # some file-like objects may not support seek

    # Parse
    try:
        if parse_as_json:
            raw = file.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
        else:
            # assume pickle by default
            data = pickle.load(file)
    except Exception as e:
        kind = "JSON" if parse_as_json else "PKL"
        raise ValueError(f"Failed to parse {kind}: {e}") from e

    # Validate & normalize
    if not isinstance(data, (list, tuple)):
        raise ValueError("pairs_for_ranking must be a list/tuple of (a, b).")

    pairs: List[Tuple[int, int]] = []
    for t in data:
        if not (isinstance(t, (list, tuple)) and len(t) == 2):
            raise ValueError(f"Invalid pair entry: {t!r}")
        a, b = int(t[0]), int(t[1])
        if a == b:
            continue
        pairs.append((a, b))

    if not pairs:
        raise ValueError("No valid pairs found in the file.")

    return pairs


def validate_pairs_in_df(df: pd.DataFrame, pairs: List[Tuple[int, int]]) -> List[int]:
    """Return list of missing patient_nums (if any)."""
    ids = set(df["patient_num"].astype(int).tolist())
    missing = []
    for a, b in pairs:
        if a not in ids: missing.append(a)
        if b not in ids: missing.append(b)
    return sorted(list(set(missing)))

def _instructions_body():
    st.markdown("""
- You will see **pairs of patients** side by side (named X and Y).
- For each patient, you will see a card with information about that patient:
  1. Age
  2. Sex              
  3. Socio-economic status 
  4. Cardiovascular risk score (SCORE2) - % risk for first CVD event in 10 years (primary prevention)
  5. Cardiovascular risk band for age (high, medium or low). 
  6. Smoking status
  7. BMI
  8. Adherence level - assessed by dispensing stats of chronic medications in the last year (if the patient has chronic medications prescribed, else 'not applicable')            
  9. Recommendations this patient currently has on C-Pi, with their estimated **relative cost**. 
- Note: in this study, we simulate the **dyslipidemia** population in C-Pi. Reccomendations and risk scores should be evaluated in this context.
- Pick which patient should be **prioritized for proactive intervention** (higher on the C-Pi focus list).
- Then choose **how sure you are** (1–5).
- When you finish all pairs, click **download results** and email us the file.
    """, unsafe_allow_html=True)

# If your Streamlit has st.dialog, we define a modal
if hasattr(st, "dialog"):
    @st.dialog("Instructions")
    def _open_instructions_dialog():
        _instructions_body()
else:
    # Fallback: we’ll use st.popover inline (no-op here)
    def _open_instructions_dialog():
        # This will be replaced with a popover in the UI placement
        pass

def _build_results_payload() -> dict:
    """Build a resume-able snapshot of the user's progress (JSON-safe)."""
    answered = [r for r in st.session_state.results if r is not None]
    return {
        "version": 1,
        "generated_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "total_pairs": int(len(st.session_state.prepared_pairs or [])),
        "answered_pairs": int(len(answered)),
        "current_index": int(st.session_state.idx or 0),
        "results": answered,  # list of [[a,b], conf] or [(a,b), conf] is fine
    }

def _serialize_results_json(payload: dict) -> tuple[bytes, str, str]:
    """Return JSON as bytes + name + mime."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return data, f"rankings_{ts}.json", "application/json"

def load_progress_json(file) -> dict:
    """Read a JSON snapshot and return the dict. Minimal validation."""
    raw = file.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict) or "results" not in data:
        raise ValueError("Invalid progress JSON.")
    return data

def apply_snapshot_to_session(snapshot: dict):
    """Merge a snapshot back into session (assumes the same prepared_pairs)."""
    st.session_state.idx = int(snapshot.get("current_index", 0))
    # Expand any tuples to lists just in case
    cleaned = []
    for item in snapshot.get("results", []):
        pair, conf = item
        a, b = pair
        cleaned.append(((int(a), int(b)), int(conf)))
    # pad to length
    total = len(st.session_state.prepared_pairs or [])
    st.session_state.results = [None] * total
    for i, val in enumerate(cleaned[:total]):
        st.session_state.results[i] = val
        
def save_progress_ui_json(key_suffix: str = ""):
    """Render inline Save (JSON) button. key_suffix keeps keys unique."""
    payload = _build_results_payload()
    data, fname, mime = _serialize_results_json(payload)

    # small right-side save button
    c1, c2 = st.columns([1, 0.22])
    with c2:
        st.download_button(
            "💾 Download progress",
            data=data,
            file_name=st.session_state.results_file_name,
            mime="application/json",
            key=f"save_json_{key_suffix}",
            help="Download a JSON snapshot of your current progress",
        )

def apply_snapshot_to_session_smart(snapshot: dict):
    """
    Map answers from a progress JSON onto the current prepared_pairs list,
    regardless of X/Y orientation or pair order in the snapshot.
    """
    prepared = st.session_state.prepared_pairs or []
    n = len(prepared)
    if n == 0:
        raise RuntimeError("No prepared_pairs in session; load pairs first.")

    # Build index map: both (a,b) and (b,a) point to the same index
    idx_map: dict[tuple[int,int], int] = {}
    for i, pr in enumerate(prepared):
        a, b = int(pr["a"]), int(pr["b"])
        idx_map[(a, b)] = i
        idx_map[(b, a)] = i

    # Initialize empty results
    results: List[Tuple[Tuple[int,int], int]] = [None] * n  # type: ignore

    placed = 0
    for item in snapshot.get("results", []):
        try:
            pair, conf = item
            a, b = int(pair[0]), int(pair[1])
            conf = int(conf)
        except Exception:
            continue  # skip malformed rows

        i = idx_map.get((a, b))
        if i is None:
            # pair not found in current session; ignore
            continue

        # Normalize stored pair to the canonical (a,b) of prepared_pairs[i]
        canon_a, canon_b = int(prepared[i]["a"]), int(prepared[i]["b"])
        results[i] = ((canon_a, canon_b), conf)
        placed += 1

    # Find next unanswered index
    try:
        next_idx = next(k for k, v in enumerate(results) if v is None)
    except StopIteration:
        next_idx = n  # done

    st.session_state.results = results
    st.session_state.idx = next_idx
    st.session_state.pair_counter = next_idx  # keep widget keys advancing
    return placed, n, next_idx

def _start_new_session():
    # jump to upload and clear artifacts safely
    st.session_state.stage = "upload"
    st.session_state.idx = 0
    st.session_state.pair_counter = 0
    st.session_state.results_downloaded = False
    st.session_state.pop("results_bytes", None)
    st.session_state.pop("results_file_name", None)
    st.rerun()



# ─────────────────────────────────────────────────────────────────────────────
# State init
if "stage" not in st.session_state:
    st.session_state.stage = "login"   # start at login
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "patient_df" not in st.session_state:
    st.session_state.patient_df = None
if "pairs" not in st.session_state:
    st.session_state.pairs = None
if "prepared_pairs" not in st.session_state:
    st.session_state.prepared_pairs = []  # list of dicts with randomized X/Y per pair
if "idx" not in st.session_state:
    st.session_state.idx = 0
if "pair_counter" not in st.session_state:
    st.session_state.pair_counter = 0     # for fresh widget keys per pair
if "results" not in st.session_state:
    st.session_state.results = []         # list of ((i, j), confidence) 
if "results_downloaded" not in st.session_state:
    st.session_state.results_downloaded = False
if "placed" not in st.session_state:
    st.session_state.placed = 0

# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# Login screen
# ─────────────────────────────────────────────────────────────
if st.session_state.get("stage") == "login" or "user_name" not in st.session_state:
    st.header("Sign in to start")
    st.caption("Enter your full name in English.")

    name = st.text_input("Your full name in English (required)", value=st.session_state.get("user_name", ""), placeholder="e.g., Dana Levi")
    if name:
        if st.button("Continue", type="primary", disabled=(len(name.strip()) < 2)):
            st.session_state.user_name = name.strip()
            st.session_state.stage = "upload"
            st.rerun()

    st.stop()  # don’t render the rest of the app until login is done

# Pages
st.title("🩺 Patients Ranking Research")

if st.session_state.stage == "upload":
    st.header("Welcome to the Ranking Project!")
    st.header("Let's get started.", divider="gray")

    st.subheader("Step 1 — Load the file you recieved by email")

    # Show status of File A (auto-loaded from repo)
    try:
        df_preview = load_patient_df_from_repo(PATIENT_DF_PATH)
        # st.success(f"File A loaded from repo: **{PATIENT_DF_PATH.name}**  •  Patients: **{len(df_preview)}**")
    except Exception as e:
        st.error(f"Problem loading data into app: {e}")

    # User only uploads File B
    pairs_file = st.file_uploader("**Pairs for ranking** (JSON file)", type=["json", "pkl"])
    st.subheader("Optional — load previous progress from this round")

    progress_file = st.file_uploader("**Optional** - load previous progress from this round (JSON)", type=["json"], key="progress_upload")

    if st.button("Start", type="primary", disabled=not pairs_file):
        # Read File A from repo
        try:
            df = load_patient_df_from_repo(PATIENT_DF_PATH)
        except Exception as e:
            st.error(f"Failed to load basic research data from repo: {e}")
            st.stop()

        # Read File B (pairs)
        try:
            pairs = read_pairs_file(pairs_file)
        except Exception as e:
            st.error(f"Failed to read pairs PKL: {e}")
            st.stop()

        st.session_state.input_filename = getattr(pairs_file, "name", "pairs.json")

        # Validate pairs exist in df
        missing = validate_pairs_in_df(df, pairs)
        if missing:
            st.error(f"The following patient_num are missing from patient_df: {missing[:20]}{'...' if len(missing)>20 else ''}")
            st.stop()

        # Prepare lookup by id
        by_id = df.set_index("patient_num").to_dict("index")

        # Precompute randomized X/Y orientation per pair (stable through the session)
        rng = random.Random(42)
        prepared = []
        for a, b in pairs:
            a_dict = normalize_patient({**by_id[a], "patient_num": a})
            b_dict = normalize_patient({**by_id[b], "patient_num": b})
            if rng.random() < 0.5:
                patient_x, patient_y = a_dict, b_dict
            else:
                patient_x, patient_y = b_dict, a_dict
            prepared.append({"a": a, "b": b, "patient_x": patient_x, "patient_y": patient_y})

        # Prime session
        st.session_state.patient_df = df
        st.session_state.pairs = pairs
        st.session_state.prepared_pairs = prepared
        st.session_state.idx = 0
        st.session_state.pair_counter = 0
        st.session_state.results = [None] * len(prepared)

        if progress_file is not None:
            try:
                snapshot = load_progress_json(progress_file)
                placed, n, next_idx = apply_snapshot_to_session_smart(snapshot)
                st.session_state.placed = placed
                st.success(f"Loaded progress: restored {placed}/{n} answers. Resuming at pair {min(next_idx+1, n)}.")
            except Exception as e:
                st.warning(f"Could not apply progress file: {e}")

        st.session_state.stage = "explain"
        st.rerun()

elif st.session_state.stage == "explain":
    total = len(st.session_state.prepared_pairs)
    unique_ids = set()
    for pr in st.session_state.prepared_pairs:
        unique_ids.add(pr["a"]); unique_ids.add(pr["b"])
    n_unique = len(unique_ids)

    st.header("Before you begin")
    st.markdown(
        """
- All the data in this study is **synthetic**, and only **simulates** real patients.
- You will see **pairs of patients** side by side (named X and Y).

- For each patient, you will see a card with information about that patient:
  1. Age
  2. Sex              
  3. Socio-economic status 
  4. Cardiovascular risk score (SCORE2) - % risk for first CVD event in 10 years (primary prevention)
  5. Cardiovascular risk band for age (high, medium or low). 
  6. Smoking status
  7. BMI
  8. Adherence level - assessed by dispensing stats of chronic medications in the last year (if the patient has chronic medications prescribed, else 'not applicable')            
  9. Recommendations this patient currently has on C-Pi, with their estimated **relative cost**. 
    """
    )

    st.markdown(
"""
- Note: in this study, we simulate the **dyslipidemia** population in C-Pi. Reccomendations and risk scores should be evaluated in this context.

- Pick which patient should be **prioritized for proactive intervention** (higher on the C-Pi focus list).  

- Then choose **how sure you are** (1–5).  

- When you finish all pairs, click **download results** and email us the file.
        """
    )
    st.info(f"Pairs to review: **{total - st.session_state.placed}**")    
 

    c1= st.columns([1])
    if st.button("Start", type="primary"):
        st.session_state.stage = "running"
        st.rerun()

elif st.session_state.stage == "running":
    # st.markdown("For the pairs below, choose which patiets should be prioritized for proactive intervention (higher on the C-Pi focus list)")
# Top row with a right-aligned help button
    left_spacer, right_btn = st.columns([1, 0.2])
    with right_btn:
        if hasattr(st, "dialog"):
            if st.button("❓ Instructions", key=f"help_{st.session_state.pair_counter}"):
                _open_instructions_dialog()
        else:
            # Fallback if st.dialog isn’t available: use a popover
            with st.popover("❓ Instructions", use_container_width=True):
                _instructions_body()

    total = len(st.session_state.prepared_pairs)
    if st.session_state.idx >= total:
        st.session_state.stage = "done"
        st.session_state.just_finished = True
        st.rerun()

    pair = st.session_state.prepared_pairs[st.session_state.idx]
    k_sel  = f"selected_{st.session_state.pair_counter}"
    k_conf = f"conf_{st.session_state.pair_counter}"

    st.markdown("#### Which patient should be prioritized for proactive intervention?")
    st.caption(f"Pair {st.session_state.idx+1} of {total}")

    # Derive output name from the uploaded file + user
    uploaded_name = st.session_state.get("input_filename", "pairs.json")
    user_name = st.session_state.get("user_name")  # from your login step
    out_name = _compose_output_filename(uploaded_name, user_name)

    # Cache once
    if "results_file_name" not in st.session_state or not st.session_state.results_file_name:
        st.session_state.results_file_name = out_name
    # NEW: save JSON on every page
    save_progress_ui_json(key_suffix=f"run_{st.session_state.pair_counter}")
    

    pX = pair["patient_x"]
    pY = pair["patient_y"]

    cat_order, per_cat_master = build_pair_recs_alignment_plan(pX, pY)
    current_choice = st.session_state.get(k_sel)

    card_x = patient_card_html("Patient X", pX, current_choice == "Patient X", side="left",
                            category_order=cat_order, per_category_master=per_cat_master)
    card_y = patient_card_html("Patient Y", pY, current_choice == "Patient Y", side="right",
                            category_order=cat_order, per_category_master=per_cat_master)

    st.markdown(f'<div class="pair-grid">{card_x}{card_y}</div>', unsafe_allow_html=True)
  
    st.markdown("")

    CONF_LABELS = {
        5: "5 - completely sure",
        4: "4 - almost",
        3: "3 - fairly",
        2: "2 - slightly",
        1: "1 - not sure, chose because I had to",
    }

    st.radio("Choose one:", ["Patient X", "Patient Y"], index=None, horizontal=True, key=k_sel)


    st.markdown("#### How sure are you?")
    st.radio(
        "On a scale of 1–5:",
        options=[5, 4, 3, 2, 1],          # values are INTs, shown top→bottom as 5→1
        format_func=lambda x: CONF_LABELS[x],
        index=None,
        horizontal=False,
        key=k_conf,                        # keep your per-pair key
    )

    choice = st.session_state.get(k_sel)   # "Patient X" | "Patient Y"
    conf   = st.session_state.get(k_conf)  # int 1..5

    can_submit = (choice is not None) and (conf is not None)
    if st.button("Submit", type="primary"):
        choice = st.session_state.get(k_sel, None)
        conf   = st.session_state.get(k_conf, None)

        # hard validation
        if choice not in ("Patient X", "Patient Y"):
            st.warning("Please choose Patient X or Patient Y before submitting.")
            st.stop()
        if conf not in (1, 2, 3, 4, 5):
            st.warning("Please choose a confidence between 1–5.")
            st.stop()

        a, b = pair["a"], pair["b"]
        if choice == "Patient X":
            chosen_id, other_id = pair["patient_x"]["id"], pair["patient_y"]["id"]
        elif choice == "Patient Y":
            chosen_id, other_id = pair["patient_y"]["id"], pair["patient_x"]["id"]

        if   (chosen_id, other_id) == (a, b): out_pair = (a, b)
        elif (chosen_id, other_id) == (b, a): out_pair = (b, a)
        else:                                 out_pair = (chosen_id, other_id)

        st.session_state.results[st.session_state.idx] = (out_pair, int(conf))
        st.session_state.idx += 1
        st.session_state.pair_counter += 1
        st.rerun()

    st.divider()

elif st.session_state.stage == "done":
# Build the payload you save (you currently save just the results list)
    results: List[Tuple[Tuple[int,int], int]] = [r for r in st.session_state.results if r is not None]
    payload = results  # or switch to _build_results_payload() if you prefer

    # Derive output name from the uploaded file + user
    uploaded_name = st.session_state.get("input_filename", "pairs.json")
    user_name = st.session_state.get("user_name")  # from your login step
    out_name = _compose_output_filename(uploaded_name, user_name)

    # Cache once
    if "results_file_name" not in st.session_state or not st.session_state.results_file_name:
        st.session_state.results_file_name = out_name

    if "results_bytes" not in st.session_state or not st.session_state.results_bytes:
        st.session_state.results_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


    file_name = st.session_state.results_file_name
    results_bytes = st.session_state.results_bytes  # guaranteed bytes, not None

    if st.session_state.get("just_finished", False) and not hasattr(st, "dialog"):
        st.warning("All pairs completed — please click **Download results** now to save your work. "
                   "If you leave or refresh without downloading, your results will be lost.")
        st.session_state.just_finished = False

    # ---- Page content ----


    # Inline download button (separate key). This also flips the same flag.
    st.write(f"Completed pairs: {len(results)}")

    clicked_inline = st.download_button(
        "⬇️ Download results",
        data=st.session_state.results_bytes,
        file_name=st.session_state.results_file_name,
        mime="application/json",
        key="dl_inline",
    )
    if not clicked_inline:
        st.warning(
        "IMPORTANT! Click **download results** now to save your work.\n"
        "If you leave or refresh without downloading, **your results will be lost**.", icon="🚨"
    )

    if clicked_inline:
        st.session_state.results_downloaded = True
        st.success("All pairs completed and downloaded. Great work!")

    st.divider()

    # Gate the restart button on the flag
    if not st.session_state.results_downloaded:
        st.info("Please download your results to enable starting a new session.")

    if st.button("Start a new session", type="primary",
                disabled=not st.session_state.results_downloaded,
                key="restart_btn"):
        # reset for a fresh run
        st.session_state.stage = "upload"
        st.session_state.idx = 0
        st.session_state.pair_counter = 0
        st.session_state.results_downloaded = False
        st.session_state.pop("results_bytes", None)
        st.session_state.pop("results_file_name", None)
        st.rerun()  # force rerun so the UI switches immediately
