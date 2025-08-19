import io, pickle, random, itertools, json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
from os import PathLike
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ranking Study", page_icon="🩺", layout="wide")


# File A lives in your repo at: <repo>/data/file_a.xlsx  (change if needed)
PATIENT_DF_PATH = (Path(__file__).parent / "patient_df.csv").resolve()

# ─────────────────────────────────────────────────────────────────────────────
# Constants & mapping (your mapping)
_RAW_REC_MAP = {
    "rec1":  {"Category": "Lab Tests",          "Short": "Basic lab panel", "DL": "Basic lab panel - LDL, HDL, TG, HbA1C, AST, ALT"},
    "rec2":  {"Category": "Lab Tests",          "Short": "Advanced lab panel", "DL": "Advanced lab panel - ApoB, ApoA1,Lpa"},
    "rec3":  {"Category": "Lab Tests",          "Short": "Pathophysiology investigation lab panel", "DL": "Genetic testing for Familial Hypercholesterolemia"},
    "rec4":  {"Category": "Lab Tests",          "Short": "Routine lab monitoring", "DL": "Routine LDL monitoring"},
    "rec5":  {"Category": "Referals",           "Short": "Diagnostic imaging", "DL": "Routine diagnostic imaging - carotid doppler"},
    "rec6":  {"Category": "Referals",           "Short": "Advanced diagnostic imaging", "DL": "Advanced diagnostic imaging - CTA/heart perfusion test"},
    "rec7":  {"Category": "Referals",           "Short": "Diagnostic procedure", "DL": "A diagnostic procedure (e.g., endoscopic procedure, stress test, holter)"},
    "rec8":  {"Category": "Referals",           "Short": "Take medical measurment", "DL": "Take BP measurment"},
    "rec9":  {"Category": "Treatment",          "Short": "Initiate preventive treatment", "DL": "Initiate preventive treatment"},
    "rec10": {"Category": "Treatment",          "Short": "Initiate first-line treatment", "DL": "Initiate first-line treatment - low dose statin"},
    "rec11": {"Category": "Treatment",          "Short": "Initiate advanced treatment", "DL": "Initiate advanced treatment - medium/high dose statin/statin+azetrol/pcsk9"},
    "rec12": {"Category": "Treatment",          "Short": "Treatment upgrade", "DL": "Treatment upgrade due to poorly controlled LDL"},
    "rec13": {"Category": "Treatment",          "Short": "Treatment replacement d/t contraindication", "DL": "Treatment replacement due to contraindication"},
    "rec14": {"Category": "Treatment",          "Short": "A medical device for treating the condition", "DL": "Strat using a medical device to treat the condition"},
    "rec15": {"Category": "Treatment",          "Short": "A medical procedure for treating the condition", "DL": "A medical procedure to treat the condition"},
    "rec16": {"Category": "Consultation",       "Short": "Specialist consultation", "DL": "Specialist consultation - Lipidologist consultation"},
    "rec17": {"Category": "Consultation",       "Short": "Other consultation", "DL": "Hepatologic consultation - due to high liver enzymes/liver disease"},
    "rec18": {"Category": "Lifestyle Changes",  "Short": "Nutritiononel consultation", "DL": "Nutritional consultation"},
    "rec19": {"Category": "Lifestyle Changes",  "Short": "Lifestyle improvement", "DL": "Lifestyle improvement - start exercises, diet adjustments"},
    "rec20": {"Category": "Lifestyle Changes",  "Short": "Stop harmful habits", "DL": "Lifestyle improvement - stop harmful habits"},
    "rec21": {"Category": "Other",              "Short": "Curate patient medical record", "DL": "Curate patient medical record"},
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
        raise ValueError("No valid pairs found in the PKL.")
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
  2. Cardiovascular risk score - % risk for CVD event in 10 years
  3. Recommendations this patient currently has on C-Pi
- Note: in this study, we simulate the **Dyslipidemia** population in C-Pi. Reccomendations and risk scores should be evaluated in this context.
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

# ─────────────────────────────────────────────────────────────────────────────
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
    pairs_file = st.file_uploader("**Pairs for ranking** (PKL file)", type=["pkl"])

    if st.button("Start", type="primary", disabled=not pairs_file):
        # Read File A from repo
        try:
            df = load_patient_df_from_repo(PATIENT_DF_PATH)
        except Exception as e:
            st.error(f"Failed to load File A from repo: {e}")
            st.stop()

        # Read File B (pairs)
        try:
            pairs = read_pairs_pkl(pairs_file)
        except Exception as e:
            st.error(f"Failed to read pairs PKL: {e}")
            st.stop()

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
- You will see **pairs of patients** side by side (named X and Y).

- For each patient, you will see a card with information about that patient:
    - **Age**
    - Cardiovascular **risk score** - % risk for CVD event in 10 years
    - **Reccomendations** this patient currently has on C-Pi

    """
    )


    st.markdown(
"""
- Note: in this study, we simulate the **Dyslipidemia** population in C-Pi. Reccomendations and risk scores should be evaluated in this context.

- Pick which patient should be **prioritized for proactive intervention** (higher on the C-Pi focus list).  

- Then choose **how sure you are** (1–5).  

- When you finish all pairs, click **download results** and email us the file.
        """
    )

    st.info(f"Pairs to review: **{total}**")    

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
        st.rerun()

    # Current pair
    pair = st.session_state.prepared_pairs[st.session_state.idx]
    k_sel  = f"selected_{st.session_state.pair_counter}"
    k_conf = f"conf_{st.session_state.pair_counter}"


    # Selector below cards
    st.markdown("#### Which patient should be prioritized for proactive intervention?")

    st.caption(f"Pair {st.session_state.idx+1} of {total}")

    # Side-by-side boxes with highlight according to current selection
    current_choice = st.session_state.get(k_sel)  # "Patient X" or "Patient Y" or None
    col1, col2 = st.columns(2)
    with col1:
        patient_card("Patient X", pair["patient_x"], current_choice == "Patient X")
    with col2:
        patient_card("Patient Y", pair["patient_y"], current_choice == "Patient Y")
    
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
    if st.button("Submit", type="primary", disabled=not can_submit):
        a, b = pair["a"], pair["b"]

        if choice == "Patient X":
            chosen_id = pair["patient_x"]["id"]
            other_id  = pair["patient_y"]["id"]
        else:
            chosen_id = pair["patient_y"]["id"]
            other_id  = pair["patient_x"]["id"]

        if (chosen_id, other_id) == (a, b):
            out_pair = (a, b)
        elif (chosen_id, other_id) == (b, a):
            out_pair = (b, a)
        else:
            out_pair = (chosen_id, other_id)  # safety fallback

        # conf is already an int
        st.session_state.results[st.session_state.idx] = (out_pair, conf)
        st.session_state.idx += 1
        st.session_state.pair_counter += 1
        st.rerun()


    st.divider()
    st.button("Restart this iteration", on_click=lambda: (
        st.session_state.update(dict(stage="upload"))
    ))

elif st.session_state.stage == "done":
    st.success("All pairs completed. Thank you!")

    results: List[Tuple[Tuple[int,int], int]] = [r for r in st.session_state.results if r is not None]
    st.write(f"Completed pairs: {len(results)}")

    # Show a preview table for convenience
    if results:
        df_prev = pd.DataFrame(
            [{"chosen": p[0][0], "other": p[0][1], "confidence": p[1]} for p in results]
        )
        st.dataframe(df_prev, use_container_width=True, hide_index=True)

    # Prepare PKL download (list of ((i, j), confidence))
    buf = io.BytesIO()
    pickle.dump(results, buf)
    st.download_button(
        "⬇️ Download results (PKL)",
        data=buf.getvalue(),
        file_name=f"rankings_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pkl",
        mime="application/octet-stream",
    )

    st.divider()
    st.button("Start a new iteration", on_click=lambda: (
        st.session_state.update(dict(stage="upload"))
    ))
