"""SQ3 Rating App — Streamlit interface with timestamped session files.

The sampler (sq3_sample_pairs.py) creates a TEMPLATE CSV that this app
never modifies. On launch, the app creates a new SESSION file with a
wall-clock timestamp, resuming from the latest existing session if any.
All ratings are written to the new session file. The latest session
file is always the canonical, up-to-date ratings set.

File layout in data/processed/sq3/:
    sq3_ratings_FB.csv                     # template (created by sampler)
    sq3_ratings_FB_20260520_143012.csv    # session 1 (created by app)
    sq3_ratings_FB_20260521_091534.csv    # session 2, resumes from above

Pass the LATEST session file (not the template) to sq3_analyze.py.

Requires: streamlit >= 1.30.

Usage:
    streamlit run scripts/sq3_rating_app.py

Configure via environment variable:
    SQ3_RATINGS_CSV=data/processed/sq3/sq3_ratings_FB.csv \\
        streamlit run scripts/sq3_rating_app.py
"""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


# --- Configuration ---------------------------------------------------------

TEMPLATE_PATH = Path(
    os.environ.get(
        "SQ3_RATINGS_CSV",
        "data/processed/sq3/sq3_ratings_FB.csv",
    )
)

EXPECTED_COLUMNS = [
    "pair_id", "target", "response",
    "rating", "category", "is_compound", "notes",
]

CATEGORIES = [
    "coordinate", "hypernym", "hyponym", "circumlocution",
    "phonological", "unrelated", "other",
]

RATING_DEFS: dict[int, tuple[str, str]] = {
    0: ("Unrelated",
        "Response and target share no recognizable semantic relation."),
    1: ("Distantly related",
        "Some thematic or contextual association, but distinct semantic "
        "categories."),
    2: ("Clearly related",
        "Same superordinate category and similar semantic profile, "
        "but a different word."),
    3: ("Synonymous",
        "Response is a near-identical or equivalent word for the target."),
}

KAMEL_ANCHORS = {0: "cykel", 1: "öken", 2: "häst, åsna", 3: "dromedar"}

# Recognize timestamped session-file names (vs the un-timestamped template).
TIMESTAMP_PATTERN = re.compile(r"_\d{8}_\d{6}\.csv$")


# --- Session file management -----------------------------------------------

def find_latest_session(template_path: Path) -> Path | None:
    """Return the most recent timestamped session file, or None."""
    stem = template_path.stem
    parent = template_path.parent
    candidates = [
        p for p in parent.glob(f"{stem}_*.csv")
        if TIMESTAMP_PATTERN.search(p.name)
    ]
    return max(candidates) if candidates else None


def initialize_session_file(template_path: Path) -> tuple[Path, Path]:
    """Create the working file for this session.

    Returns (new_session_path, source_path). source_path is either an
    existing session file (resume) or the template (fresh start).
    """
    stem = template_path.stem
    parent = template_path.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_path = parent / f"{stem}_{timestamp}.csv"

    latest = find_latest_session(template_path)
    source = latest if latest is not None else template_path

    if not source.exists():
        raise FileNotFoundError(
            f"No previous session file found and template {template_path} "
            f"does not exist. Run sq3_sample_pairs.py first."
        )

    shutil.copy(source, new_path)
    print(f"[sq3_rating_app] Session file: {new_path}")
    print(f"[sq3_rating_app] Resumed from: {source}")
    return new_path, source


# --- IO helpers ------------------------------------------------------------

def load_ratings(path: Path) -> pd.DataFrame:
    """Load the ratings CSV with explicit nullable dtypes.

    pd.read_csv on an all-empty column infers float64, which then refuses
    assignment of bool/int/string values via df.at. The dtype normalization
    here is what fixes the "Invalid value 'False' for dtype 'float64'"
    class of error.
    """
    if not path.exists():
        st.error(
            f"CSV not found: `{path}`. Set SQ3_RATINGS_CSV or place the "
            f"file at the default path."
        )
        st.stop()

    df = pd.read_csv(path)

    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        st.error(f"CSV at `{path}` is missing columns: {sorted(missing)}.")
        st.stop()

    df = df[EXPECTED_COLUMNS].copy()

    # Nullable Int64 for rating so 0-3 values coexist with NaN.
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").astype("Int64")

    # Nullable string for text columns.
    for col in ["pair_id", "target", "response", "category", "notes"]:
        df[col] = df[col].astype("string")

    # Nullable boolean for is_compound, coerced from various input forms.
    df["is_compound"] = (
        df["is_compound"]
        .map(
            lambda x: pd.NA
            if pd.isna(x) or str(x).strip() == ""
            else (str(x).strip().lower() in {"true", "1", "yes"})
        )
        .astype("boolean")
    )

    return df


def save_ratings(df: pd.DataFrame, path: Path) -> None:
    """Atomic write via tempfile + rename."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)


def values_differ(a, b) -> bool:
    """Safe equality test that handles pd.NA correctly.

    Direct `a != b` returns pd.NA when either side is pd.NA, which is
    not boolean-truthy and raises in an `if` context.
    """
    if pd.isna(a) and pd.isna(b):
        return False
    if pd.isna(a) or pd.isna(b):
        return True
    return a != b


def get_rating(row) -> int | None:
    val = row["rating"]
    if pd.isna(val) or str(val).strip() == "":
        return None
    return int(float(val))


def get_str(row, col) -> str | None:
    val = row[col]
    if pd.isna(val) or str(val).strip() == "":
        return None
    return str(val)


def get_bool(row, col) -> bool:
    val = row[col]
    if pd.isna(val) or str(val).strip() == "":
        return False
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in {"true", "1", "yes"}


def is_rated(row) -> bool:
    return get_rating(row) is not None


# --- Session state ---------------------------------------------------------

def init_state() -> None:
    if "session_path" not in st.session_state:
        try:
            new_path, source = initialize_session_file(TEMPLATE_PATH)
        except FileNotFoundError as e:
            st.error(str(e))
            st.stop()
        st.session_state.session_path = new_path
        st.session_state.source_path = source
        st.session_state.resumed = (source != TEMPLATE_PATH)
        st.session_state.last_saved_at = None
    if "df" not in st.session_state:
        st.session_state.df = load_ratings(st.session_state.session_path)
    if "idx" not in st.session_state:
        df = st.session_state.df
        unrated = [i for i in df.index if not is_rated(df.loc[i])]
        st.session_state.idx = int(unrated[0]) if unrated else 0


# --- App -------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="SQ3 Rating", layout="centered")
    init_state()

    df = st.session_state.df
    n = len(df)
    idx = st.session_state.idx
    row = df.iloc[idx]
    pair_id = str(row["pair_id"])
    rated_n = sum(is_rated(df.loc[i]) for i in df.index)

    # Status header — visible at top, updates on every save.
    save_status = (
        f"✓ Saved at {st.session_state.last_saved_at.strftime('%H:%M:%S')}"
        if st.session_state.last_saved_at
        else "No saves yet this session"
    )
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        c1.markdown(
            f"**Session file:** `{st.session_state.session_path.name}`  \n"
            f"{save_status}"
        )
        c2.markdown(f"**{rated_n} / {n} rated**")

    if st.session_state.resumed:
        st.caption(
            f"Resumed from previous session: "
            f"`{st.session_state.source_path.name}`"
        )

    st.markdown(f"### Pair {idx + 1} of {n}")
    st.progress(rated_n / n if n else 0)

    # The pair
    st.markdown("---")
    c1, c2 = st.columns(2)
    c1.markdown("**Target**")
    c1.markdown(f"## {row['target']}")
    c2.markdown("**Response**")
    c2.markdown(f"## {row['response']}")
    st.markdown("---")

    # Rating
    st.markdown("**How similar is the response to the target?**")
    cur_rating = get_rating(row)
    rating = st.radio(
        label="Rating",
        options=[0, 1, 2, 3],
        format_func=lambda x: f"{x} — {RATING_DEFS[x][0]}",
        horizontal=True,
        index=cur_rating,
        label_visibility="collapsed",
        key=f"rating_{pair_id}",
    )
    if rating is not None:
        st.caption(RATING_DEFS[rating][1])

    # Category
    st.markdown("**Category**")
    cur_category = get_str(row, "category")
    cat_options = ["(not yet selected)"] + CATEGORIES
    cat_idx = (
        cat_options.index(cur_category)
        if cur_category in CATEGORIES
        else 0
    )
    category_choice = st.selectbox(
        label="Category",
        options=cat_options,
        index=cat_idx,
        label_visibility="collapsed",
        key=f"cat_{pair_id}",
    )
    category = (
        None if category_choice == "(not yet selected)" else category_choice
    )

    # Compound flag
    is_compound = st.checkbox(
        "Response is a compound word",
        value=get_bool(row, "is_compound"),
        key=f"comp_{pair_id}",
    )

    # Notes
    notes = st.text_area(
        "Notes (optional)",
        value=get_str(row, "notes") or "",
        key=f"notes_{pair_id}",
        height=70,
    )

    # Persistence — ONLY when rating is set. This is what prevents the
    # checkbox-default-False issue (an unvisited pair with rating=None
    # would otherwise write is_compound=False on first render).
    if rating is not None:
        new_values = {
            "rating": rating,
            "category": category if category else pd.NA,
            "is_compound": bool(is_compound),
            "notes": notes if notes else pd.NA,
        }
        changed = False
        for col, val in new_values.items():
            existing = df.at[idx, col]
            if values_differ(existing, val):
                df.at[idx, col] = val
                changed = True
        if changed:
            save_ratings(df, st.session_state.session_path)
            st.session_state.df = df
            st.session_state.last_saved_at = datetime.now()
            # Re-render so the save indicator at the top reflects this save.
            st.rerun()

    # Navigation
    st.markdown("---")
    nav = st.columns([1, 1, 2, 1])
    if nav[0].button("← Previous", disabled=(idx == 0)):
        st.session_state.idx = idx - 1
        st.rerun()
    if nav[1].button("Next →", disabled=(idx == n - 1)):
        st.session_state.idx = idx + 1
        st.rerun()
    jump = nav[3].number_input(
        "Jump to pair",
        min_value=1, max_value=n, value=idx + 1, step=1,
        label_visibility="collapsed",
    )
    if jump != idx + 1:
        st.session_state.idx = int(jump) - 1
        st.rerun()

    if rated_n == n:
        st.success(
            f"All pairs rated. Pass this file to `sq3_analyze.py`:  \n"
            f"`{st.session_state.session_path}`"
        )

    # Rubric
    with st.expander("Rubric and anchor examples"):
        st.markdown("**Rating scale (0–3)**")
        for r in [0, 1, 2, 3]:
            st.markdown(
                f"- **{r} — {RATING_DEFS[r][0]}** · {RATING_DEFS[r][1]}  \n"
                f"  *Anchor for target = kamel*: `{KAMEL_ANCHORS[r]}`"
            )
        st.markdown("---")
        st.markdown("**Categories**  ")
        st.markdown(
            "- **coordinate** — same-level semantic neighbour  \n"
            "- **hypernym** — category label that includes the target  \n"
            "- **hyponym** — more specific instance subsumed by the target  \n"
            "- **circumlocution** — multi-word description  \n"
            "- **phonological** — sound-alike, different meaning  \n"
            "- **unrelated** — no apparent relation  \n"
            "- **other** — anything else; add a note"
        )
        st.markdown("---")
        st.markdown("**Compound flag**  ")
        st.markdown(
            "Tick if the response is a Swedish noun compound or "
            "morphologically transparent multi-morpheme word "
            "(e.g. `puckelkamel`, `hårkam`, `dörrlås`). Independent "
            "of the primary category."
        )


if __name__ == "__main__":
    main()