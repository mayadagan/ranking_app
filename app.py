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


st.set_page_config(page_title="Ranking Study", page_icon="🩺", layout="wide")

def patient_card_html(label: str, p: dict, selected: bool) -> str:
    years_label = "year" if int(p["age"]) == 1 else "years"
    sel = " selected" if selected else ""
    recs_html = "".join(f"<li>{r}</li>" for r in p["recommendations"])
    # note: everything starts at column 0, no leading spaces/newlines
    return (
        f'<div class="card{sel}">'
        f"<h4>{label}</h4>"
        f"<p><b>Age:</b> {p['age']} {years_label}</p>"
        f"<p><b>CVD risk</b>: {p['risk']}%</p>"
        f"<p><b>Current C-Pi recommendations:</b></p>"
        f"<ul>{recs_html}</ul>"
        "</div>"
    )

st.markdown("""
<style>
/* ---- Theme-aware tokens ---- */
:root{
  --card-bg: #ffffff;
  --card-border: #dddddd;
  --card-shadow: 0 2px 6px rgba(0,0,0,.06);
  --card-selected-bg: #f0fff4;   /* light green tint */
  --card-selected-border: #34c759;
}
@media (prefers-color-scheme: dark){
  :root{
    --card-bg: #1e1e1e;
    --card-border: #3a3a3a;
    --card-shadow: 0 2px 10px rgba(0,0,0,.55);
    --card-selected-bg: #132a1b; /* darker green tint for dark mode */
    --card-selected-border: #2ecc71;
  }
}

/* ---- Layout & cards ---- */
.pair-grid{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:16px;
  align-items:stretch;             /* same height for both cards */
}
.pair-grid .card{
  background: var(--card-bg);
  border: 3px solid var(--card-border);
  border-radius:12px;
  padding:16px;
  box-shadow: var(--card-shadow);
  height:100%;
  color: inherit;                  /* follow Streamlit theme text color */
  transition: border-color .15s ease, background .15s ease;
}
.pair-grid .card.selected{
  background: var(--card-selected-bg);
  border-color: var(--card-selected-border);
}
.pair-grid .card h4{ margin-top:0; }
.pair-grid .card ul{ margin-bottom:0; padding-left: 1.1rem; }
.pair-grid .card li{ margin: .25rem 0; }
</style>
""", unsafe_allow_html=True)

# File A lives in your repo at: <repo>/data/file_a.xlsx  (change if needed)
PATIENT_DF_PATH = (Path(__file__).parent / "patient_df.csv").resolve()

# ─────────────────────────────────────────────────────────────────────────────
# Constants & mapping (your mapping)
_RAW_REC_MAP = {
    "rec1":  {"Category": "Lab Tests",          "Short": "Basic lab panel", "DL": "Basic lab panel (LDL, HDL, TG, HbA1C, AST, ALT)"},
    "rec2":  {"Category": "Lab Tests",          "Short": "Advanced lab panel", "DL": "Advanced lab panel (Lipoprotein(a), ApoB, ApoA1)"},
    "rec3":  {"Category": "Lab Tests",          "Short": "Pathophysiology investigation lab panel", "DL": "Pathophysiology-directed lab panel (genetic testing for Familial Hypercholesterolemia)"},
    "rec4":  {"Category": "Lab Tests",          "Short": "Routine lab monitoring", "DL": "Routine lab monitoring (routine LDL monitoring)"},
    "rec5":  {"Category": "Referals",           "Short": "Diagnostic imaging", "DL": "Routine diagnostic imaging (carotid doppler)"},
    "rec6":  {"Category": "Referals",           "Short": "Advanced diagnostic imaging", "DL": "Advanced diagnostic imaging (CTA / heart perfusion test)"},
    "rec7":  {"Category": "Referals",           "Short": "Diagnostic procedure", "DL": "Diagnostic procedure (endoscopic procedure, stress test, holter)"},
    "rec8":  {"Category": "Referals",           "Short": "Take medical measurment", "DL": "Medical measurment (take BP measurment)"},
    "rec9":  {"Category": "Treatment",          "Short": "Initiate preventive treatment", "DL": "Initiate preventive treatment"},
    "rec10": {"Category": "Treatment",          "Short": "Initiate first-line treatment", "DL": "Initiate first-line treatment (low dose statin)"},
    "rec11": {"Category": "Treatment",          "Short": "Initiate advanced treatment", "DL": "Initiate advanced treatment (medium/high dose statin / statin+azetrol / PCSK9)"},
    "rec12": {"Category": "Treatment",          "Short": "Treatment upgrade", "DL": "Treatment upgrade (upgrade due to poorly controlled LDL)"},
    "rec13": {"Category": "Treatment",          "Short": "Treatment replacement d/t contraindication", "DL": "Treatment replacement due to contraindication"},
    "rec14": {"Category": "Treatment",          "Short": "A medical device for treating the condition", "DL": "Medical device (start using a medical device to treat the condition)"},
    "rec15": {"Category": "Treatment",          "Short": "A medical procedure for treating the condition", "DL": "Medical procedure (a medical procedure to treat the condition"},
    "rec16": {"Category": "Consultation",       "Short": "Specialist consultation", "DL": "Specialist consultation (lipidologist consultation)"},
    "rec17": {"Category": "Consultation",       "Short": "Other consultation", "DL": "Other consultation (hepatologic consultation due to high liver enzymes / liver disease)"},
    "rec18": {"Category": "Lifestyle Changes",  "Short": "Nutritional consultation", "DL": "Nutritional consultation"},
    "rec19": {"Category": "Lifestyle Changes",  "Short": "Lifestyle improvement", "DL": "Lifestyle improvement (start exercise, diet adjustments)"},
    "rec20": {"Category": "Lifestyle Changes",  "Short": "Stop harmful habits", "DL": "Lifestyle improvement (stop harmful habits)"},
    "rec21": {"Category": "Other",              "Short": "Curate patient medical record", "DL": "Curate medical record (add diagnosis of dyslipidemia to patient's file)"},
}

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
    required = {"patient_num", "age", "risk"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"patient_df missing required columns: {missing}")

    # Ensure rec1..rec21 exist and are ints
    for i in range(1, 22):
        col = f"rec{i}"
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].fillna(0).astype(int)

    df["patient_num"] = df["patient_num"].astype(int)
    df["age"] = df["age"].astype(int)
    df["risk"] = df["risk"].astype(int)
    return df

import re

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
    return out or ["(no active recommendations)"]

def normalize_patient(row_dict: dict) -> dict:
    return {
        "id": int(row_dict.get("patient_num")),
        "age": int(row_dict.get("age")),
        "risk": int(row_dict.get("risk")),
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
    required = {"patient_num", "age", "risk"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"patient_df missing required columns: {missing}")

    # Ensure rec1..rec21 exist (fill with 0 if absent)
    for i in range(1, 22):
        col = f"rec{i}"
        if col not in df.columns:
            df[col] = 0

    # Coerce dtypes
    df["patient_num"] = df["patient_num"].astype(int)
    df["age"] = df["age"].astype(int)
    df["risk"] = df["risk"].astype(int)
    for i in range(1, 22):
        df[f"rec{i}"] = df[f"rec{i}"].fillna(0).astype(int)

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
- For each patient you’ll get:
  1. Age
  2. Cardiovascular risk score - % risk for first CVD event in 10 years (primary prevention)
  3. Recommendations this patient currently has on C-Pi
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
# UI building blocks
def patient_card(label: str, p: dict, selected: bool):
    bg = "#f0fff4" if selected else "#ffffff"
    border = "#34c759" if selected else "#ddd"
    years_label = "year" if int(p["age"]) == 1 else "years"
    st.markdown(
        f"""
        <div style="
            border: 3px solid {border};
            border-radius: 12px;
            padding: 16px;
            background-color: {bg};
            box-shadow: 0 2px 6px rgba(0,0,0,0.04);
            min-height: 220px;
        ">
            <h4 style="margin-top:0">{label}</h4>
            <p><b>Age:</b> {p['age']} {years_label}</p>
            <p><b>CVD risk</b>: {p['risk']}%</p>
            <p><b>Current C-Pi recommendations:</b></p>
            <ul>
                {''.join(f"<li>{r}</li>" for r in p['recommendations'])}
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

# ─────────────────────────────────────────────────────────────────────────────
# State init
if "stage" not in st.session_state:
    st.session_state.stage = "login"   # start at login
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "stage" not in st.session_state:
    st.session_state.stage = "upload"   # "upload" -> "running" -> "done"
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
            st.error(f"Failed to load File A from repo: {e}")
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
    - **Age**
    - Cardiovascular **risk score** - % risk for first CVD event in 10 years (primary prevention)
    - **Reccomendations** this patient currently has on C-Pi

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
    
    # Side-by-side boxes with highlight according to current selection
    current_choice = st.session_state.get(k_sel)  # "Patient X" / "Patient Y" / None
    card_x = patient_card_html("Patient X", pair["patient_x"], current_choice == "Patient X")
    card_y = patient_card_html("Patient Y", pair["patient_y"], current_choice == "Patient Y")

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
    # if st.button("Submit", type="primary", disabled=not can_submit):


    #     a, b = pair["a"], pair["b"]

    #     if choice == "Patient X":
    #         chosen_id = pair["patient_x"]["id"]
    #         other_id  = pair["patient_y"]["id"]
    #     else:
    #         chosen_id = pair["patient_y"]["id"]
    #         other_id  = pair["patient_x"]["id"]

    #     if (chosen_id, other_id) == (a, b):
    #         out_pair = (a, b)
    #     elif (chosen_id, other_id) == (b, a):
    #         out_pair = (b, a)
    #     else:
    #         out_pair = (chosen_id, other_id)  # safety fallback

    #     # conf is already an int
    #     st.session_state.results[st.session_state.idx] = (out_pair, conf)
    #     st.session_state.idx += 1
    #     st.session_state.pair_counter += 1
    #     st.rerun()

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
