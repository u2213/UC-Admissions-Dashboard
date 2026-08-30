"""UC Admissions Data Explorer.

This Streamlit app reads the UC admissions CSV exports from the project root
and provides a filtered view of Bay Area admissions outcomes.
"""

from __future__ import annotations

import base64
from pathlib import Path
import re
from typing import Iterable, Mapping

import pandas as pd
import plotly.express as px
import plotly.io as pio
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="UC Admissions Data Explorer",
    page_icon="UC",
    layout="wide",
)

PROJECT_ROOT = Path(__file__).resolve().parent


def locate_google_sans_font() -> Path | None:
    """Find an uploaded Google Sans font, if one is available."""
    search_dirs = (PROJECT_ROOT, PROJECT_ROOT / "attached_assets")
    candidates = [
        path
        for directory in search_dirs
        if directory.is_dir()
        for path in directory.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".woff2", ".woff", ".ttf"}
        and "google" in path.name.lower()
        and "sans" in path.name.lower()
    ]
    return sorted(candidates, key=lambda path: path.name.lower())[0] if candidates else None


google_sans_path = locate_google_sans_font()
if google_sans_path is not None:
    font_mime = {
        ".woff2": "font/woff2",
        ".woff": "font/woff",
        ".ttf": "font/ttf",
    }[google_sans_path.suffix.lower()]
    font_data = base64.b64encode(google_sans_path.read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <style>
        @font-face {{
            font-family: "Google Sans";
            src: url("data:{font_mime};base64,{font_data}") format("{google_sans_path.suffix.lower().lstrip('.')}");
            font-style: normal;
            font-weight: 100 900;
            font-display: swap;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

CHART_TEXT = "#F8FAFC"
CHART_MUTED = "#B9C2D0"
CHART_GRID = "rgba(255, 255, 255, 0.12)"
CHART_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": "reset",
    "responsive": True,
}

st.markdown(
    """
    <style>
    :root {
        color-scheme: dark;
        --app-bg: #070A0F;
        --app-text: #F8FAFC;
        --app-muted: #B9C2D0;
        --app-subtle: #AAB5C5;
        --panel-fill: rgba(255, 255, 255, 0.035);
        --panel-border: rgba(255, 255, 255, 0.11);
        --header-fill: rgba(7, 10, 15, 0.80);
        --grid-line: rgba(255, 255, 255, 0.10);
    }

    .stApp {
        background:
            radial-gradient(circle at 12% 8%, rgba(84, 102, 138, 0.17), transparent 28rem),
            radial-gradient(circle at 86% 18%, rgba(63, 82, 126, 0.13), transparent 26rem),
            var(--app-bg);
        color: var(--app-text);
        font-family: "Google Sans", Arial, sans-serif;
    }

    .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        z-index: 0;
        pointer-events: none;
        opacity: 0.16;
        background-image:
            linear-gradient(var(--grid-line) 1px, transparent 1px),
            linear-gradient(90deg, var(--grid-line) 1px, transparent 1px);
        background-size: 48px 48px;
        mask-image: linear-gradient(to bottom, black 0%, transparent 92%);
    }

    header[data-testid="stHeader"] {
        background: var(--header-fill);
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }

    .stMainBlockContainer,
    .main .block-container {
        position: relative;
        z-index: 1;
        max-width: 1440px;
        padding-top: 2.4rem;
        padding-bottom: 5rem;
    }

    .stMainBlockContainer *,
    .main .block-container * {
        font-family: "Google Sans", Arial, sans-serif;
    }

    [data-testid="stSidebar"] {
        background: var(--app-bg);
        border-right: 1px solid rgba(255, 255, 255, 0.10);
    }

    [data-testid="stSidebar"] * {
        color: var(--app-text);
    }

    [data-testid="stSidebar"] .stCaption {
        color: var(--app-subtle);
    }

    .hero-kicker {
        color: var(--app-subtle);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        margin-bottom: 0.8rem;
        text-transform: uppercase;
    }

    .hero-title {
        color: var(--app-text);
        font-size: clamp(2.4rem, 5vw, 4.8rem);
        font-weight: 760;
        letter-spacing: -0.055em;
        line-height: 0.98;
        margin: 0;
        max-width: 900px;
        text-wrap: balance;
        animation: titleDrift 8s ease-in-out infinite;
        text-shadow: 0 0 42px rgba(183, 203, 235, 0.16);
    }

    .hero-copy {
        color: var(--app-muted);
        font-size: 1.06rem;
        line-height: 1.65;
        margin: 1.35rem 0 2.2rem;
        max-width: 820px;
    }

    .stMainBlockContainer h2,
    .stMainBlockContainer h3,
    .section-title {
        color: var(--app-text);
        position: relative;
        will-change: transform, opacity;
        animation: headingEntry 700ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    .section-title {
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.035em;
        margin: 1.55rem 0 0.7rem;
    }

    .methodology-title {
        color: var(--app-text);
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 2rem 0 0.7rem;
    }

    [data-testid="stMetric"] {
        background: linear-gradient(145deg, var(--panel-fill), rgba(255, 255, 255, 0.025));
        border: 1px solid var(--panel-border);
        border-radius: 16px;
        box-shadow: 0 16px 42px rgba(0, 0, 0, 0.18);
        min-height: 132px;
        padding: 1.15rem 1.25rem;
    }

    [data-testid="stMetricLabel"] {
        color: var(--app-subtle);
    }

    [data-testid="stMetricValue"] {
        color: var(--app-text);
        letter-spacing: -0.04em;
    }

    .stPlotlyChart {
        background: var(--panel-fill);
        border: 1px solid var(--panel-border);
        border-radius: 16px;
        box-shadow: 0 18px 48px rgba(0, 0, 0, 0.16);
        padding: 0.4rem;
        animation: chartReveal 650ms cubic-bezier(0.22, 1, 0.36, 1) both;
    }

    div[data-testid="stExpander"] {
        background: var(--panel-fill);
        border: 1px solid var(--panel-border);
        border-radius: 14px;
    }

    .filter-bar-title {
        color: var(--app-text);
        font-size: 0.92rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        margin-bottom: 0.5rem;
    }

    .filter-bar-note {
        color: var(--app-subtle);
        font-size: 0.76rem;
        margin-top: 0.8rem;
    }

    .ambient-spheres {
        inset: 0;
        overflow: hidden;
        pointer-events: none;
        position: fixed;
        z-index: 0;
    }

    .ambient-sphere {
        border-radius: 50%;
        filter: blur(0.2px);
        opacity: 0.30;
        position: absolute;
        transform: translate3d(0, 0, 0);
        will-change: transform;
    }

    .sphere-one {
        background:
            radial-gradient(circle at 32% 28%, rgba(255, 255, 255, 0.42), transparent 8%),
            radial-gradient(circle at 40% 36%, rgba(143, 174, 220, 0.28), transparent 42%),
            radial-gradient(circle at 68% 74%, rgba(23, 31, 55, 0.98), rgba(6, 9, 16, 0.98) 72%);
        height: 20rem;
        right: -7rem;
        top: 12rem;
        width: 20rem;
        animation: sphereFloatOne 17s ease-in-out infinite;
    }

    .sphere-two {
        background:
            radial-gradient(circle at 28% 25%, rgba(255, 255, 255, 0.25), transparent 7%),
            radial-gradient(circle at 44% 42%, rgba(120, 143, 188, 0.24), transparent 40%),
            radial-gradient(circle at 70% 72%, rgba(17, 24, 43, 0.98), rgba(5, 8, 14, 0.98) 74%);
        bottom: 12rem;
        height: 12rem;
        left: -4rem;
        width: 12rem;
        animation: sphereFloatTwo 21s ease-in-out infinite;
    }

    @keyframes titleDrift {
        0%, 100% { transform: translate3d(0, 0, 0); }
        50% { transform: translate3d(0, -3px, 0); }
    }

    @keyframes sphereFloatOne {
        0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
        50% { transform: translate3d(-18px, 24px, 0) scale(1.035); }
    }

    @keyframes sphereFloatTwo {
        0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
        50% { transform: translate3d(20px, -18px, 0) scale(0.97); }
    }

    @keyframes chartReveal {
        from {
            opacity: 0;
            transform: translate3d(0, 10px, 0) scale(0.995);
        }
        to {
            opacity: 1;
            transform: translate3d(0, 0, 0) scale(1);
        }
    }

    @supports (animation-timeline: scroll()) {
        .sphere-one {
            animation: sphereParallax linear both;
            animation-range: 0% 85%;
            animation-timeline: scroll();
        }

        .sphere-two {
            animation: sphereParallaxReverse linear both;
            animation-range: 0% 85%;
            animation-timeline: scroll();
        }

        .hero-title {
            animation: titleParallax linear both;
            animation-range: 0% 65%;
            animation-timeline: scroll();
        }
    }

    @keyframes sphereParallax {
        from { transform: translate3d(0, -30px, 0) scale(1); }
        to { transform: translate3d(-46px, 92px, 0) scale(1.06); }
    }

    @keyframes sphereParallaxReverse {
        from { transform: translate3d(0, 28px, 0) scale(1); }
        to { transform: translate3d(38px, -70px, 0) scale(0.94); }
    }

    @keyframes titleParallax {
        from { transform: translate3d(0, 0, 0); }
        to { transform: translate3d(0, -28px, 0); }
    }

    @keyframes headingEntry {
        from {
            opacity: 0.72;
            transform: translate3d(0, 20px, 0);
        }
        to {
            opacity: 1;
            transform: translate3d(0, 0, 0);
        }
    }

    @keyframes headingScrollParallax {
        0% {
            opacity: 0.70;
            transform: translate3d(0, 30px, 0) scale(0.985);
        }
        42% {
            opacity: 1;
            transform: translate3d(0, 0, 0) scale(1);
        }
        100% {
            opacity: 0.92;
            transform: translate3d(0, -26px, 0) scale(0.99);
        }
    }

    @media (prefers-reduced-motion: reduce) {
        .hero-title,
        .ambient-sphere,
        .stPlotlyChart {
            animation: none;
        }
    }

    @media (prefers-reduced-motion: no-preference) {
        .hero-title,
        .stMainBlockContainer h2,
        .stMainBlockContainer h3,
        .section-title {
            animation-duration: 900ms;
        }
    }

    @supports (animation-timeline: view()) {
        .stMainBlockContainer h2,
        .stMainBlockContainer h3,
        .section-title {
            animation: headingScrollParallax linear both;
            animation-range: entry 0% exit 100%;
            animation-timeline: view(block);
        }
    }
    </style>
    <div class="ambient-spheres" aria-hidden="true">
        <div class="ambient-sphere sphere-one"></div>
        <div class="ambient-sphere sphere-two"></div>
    </div>
    """,
    unsafe_allow_html=True,
)


DATASET_FILES: Mapping[str, str] = {
    "modeling": "bay_area_modeling_table.csv",
    "dashboard": "dashboard_data.csv",
    "ethnicity": "uc_admissions_summary_by_ethnicity.csv",
    "freshman": "uc_freshman_admission_by_discipline.csv",
    "transfer": "uc_transfer_admission_by_major.csv",
}
SYSTEMWIDE = "__systemwide__"


APPLICANT_COLUMNS = (
    "total_applicants",
    "applicants",
    "applicant_count",
    "application_count",
    "applications",
    "total_applications",
    "number_of_applicants",
    "num_applicants",
)
ADMIT_COLUMNS = (
    "total_admits",
    "admits",
    "admitted",
    "admit_count",
    "admissions",
    "number_of_admits",
    "num_admits",
)
RATE_COLUMNS = (
    "admit_rate",
    "actual_admit_rate",
    "observed_admit_rate",
    "acceptance_rate",
    "admission_rate",
    "rate",
)
EXPECTED_RATE_COLUMNS = (
    "expected_admit_rate",
    "expected_rate",
    "predicted_admit_rate",
    "baseline_admit_rate",
    "modeled_admit_rate",
)
CAMPUS_COLUMNS = ("campus", "uc_campus", "uc", "university", "institution")
HIGH_SCHOOL_COLUMNS = (
    "high_school",
    "high_school_name",
    "school",
    "school_name",
    "highschool",
)
TERM_COLUMNS = (
    "fall_term",
    "fall_year",
    "term",
    "year",
    "admission_year",
    "academic_year",
)
ETHNICITY_COLUMNS = (
    "ethnicity",
    "ethnic_group",
    "ethnicity_group",
    "race_ethnicity",
    "race",
)


def normalize_label(value: object) -> str:
    """Normalize a column label for flexible matching."""
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def find_column(
    frame: pd.DataFrame,
    candidates: Iterable[str],
) -> str | None:
    """Find a column by exact normalized name, then by a safe substring match."""
    normalized = {normalize_label(column): str(column) for column in frame.columns}
    candidate_labels = [normalize_label(candidate) for candidate in candidates]

    for candidate in candidate_labels:
        if candidate in normalized:
            return normalized[candidate]

    for candidate in candidate_labels:
        for normalized_name, original_name in normalized.items():
            if candidate and candidate in normalized_name:
                return original_name
    return None


def numeric_series(series: pd.Series) -> pd.Series:
    """Convert counts and rates to numbers while tolerating common CSV formats."""
    cleaned = (
        series.astype("string")
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("—", "", regex=False)
        .str.replace("–", "", regex=False)
        .str.strip()
    )
    return pd.to_numeric(cleaned, errors="coerce")


def rate_series(series: pd.Series) -> pd.Series:
    """Return rates as decimals, accepting either 0–1 or 0–100 inputs."""
    values = numeric_series(series)
    non_null = values.dropna()
    if not non_null.empty and non_null.median() > 1:
        values = values / 100
    return values.clip(lower=0, upper=1)


def find_observed_rate_column(frame: pd.DataFrame) -> str | None:
    """Find an observed rate without accidentally selecting an expected-rate field."""
    column = find_column(frame, RATE_COLUMNS)
    if column is not None:
        normalized = normalize_label(column)
        if any(
            marker in normalized
            for marker in ("expected", "predicted", "baseline", "modeled")
        ):
            return None
    return column


def term_series(series: pd.Series) -> pd.Series:
    """Extract a fall year from numeric values or labels such as 2022-23."""
    values = numeric_series(series)
    extracted = pd.to_numeric(
        series.astype("string").str.extract(r"((?:19|20)\d{2})", expand=False),
        errors="coerce",
    )
    return values.where(values.between(1900, 2100), extracted)


def locate_dataset(filename: str) -> Path | None:
    """Look in the root and match timestamped uploaded filenames when needed."""
    candidates = (
        PROJECT_ROOT / filename,
        PROJECT_ROOT / "attached_assets" / filename,
    )
    exact_match = next((path for path in candidates if path.is_file()), None)
    if exact_match is not None:
        return exact_match

    uploaded_dir = PROJECT_ROOT / "attached_assets"
    timestamped_matches = sorted(
        uploaded_dir.glob(f"{Path(filename).stem}_*.csv"),
        key=lambda path: path.name,
    )
    return timestamped_matches[-1] if timestamped_matches else None


@st.cache_data(show_spinner=False)
def load_csv(filename: str) -> pd.DataFrame | None:
    path = locate_dataset(filename)
    if path is None:
        return None
    return pd.read_csv(path, low_memory=False)


def campus_label(value: str) -> str:
    """Use familiar short labels in the campus selector without changing filtering."""
    text = str(value).strip()
    lowered = text.lower()
    names = (
        ("berkeley", "Berkeley"),
        ("los angeles", "UCLA"),
        ("ucla", "UCLA"),
        ("davis", "Davis"),
        ("irvine", "Irvine"),
        ("merced", "Merced"),
        ("riverside", "Riverside"),
        ("san diego", "UC San Diego"),
        ("ucsd", "UC San Diego"),
        ("santa barbara", "UC Santa Barbara"),
        ("ucsb", "UC Santa Barbara"),
        ("santa cruz", "UC Santa Cruz"),
        ("ucsc", "UC Santa Cruz"),
        ("san francisco", "UCSF"),
    )
    for needle, label in names:
        if needle in lowered:
            return label
    return text


def is_systemwide(value: object) -> bool:
    lowered = str(value).strip().lower()
    return (
        "systemwide" in lowered
        or "universitywide" in lowered
        or lowered in {"all", "all campuses", "uc system"}
    )


def unique_text_values(frames: Iterable[pd.DataFrame], column_candidates: Iterable[str]) -> list[str]:
    values: set[str] = set()
    for frame in frames:
        column = find_column(frame, column_candidates)
        if column is not None:
            values.update(
                value
                for value in frame[column].dropna().astype(str).str.strip()
                if value
            )
    return sorted(values, key=lambda value: campus_label(value).lower())


def filter_frame(
    frame: pd.DataFrame,
    selected_campus: str,
    selected_high_schools: list[str],
    selected_terms: tuple[int, int],
) -> pd.DataFrame:
    """Apply shared sidebar filters only when their corresponding columns exist."""
    filtered = frame.copy()

    campus_column = find_column(filtered, CAMPUS_COLUMNS)
    if campus_column is not None and selected_campus == SYSTEMWIDE:
        systemwide_mask = filtered[campus_column].map(is_systemwide)
        if systemwide_mask.any():
            filtered = filtered.loc[systemwide_mask]
    elif campus_column is not None and selected_campus != SYSTEMWIDE:
        selected = str(selected_campus).strip().casefold()
        campus_values = filtered[campus_column].astype(str).str.strip()
        exact_mask = campus_values.str.casefold().eq(selected)
        if not exact_mask.any():
            exact_mask = campus_values.map(campus_label).str.casefold().eq(
                campus_label(selected_campus).casefold()
            )
        filtered = filtered.loc[exact_mask]

    term_column = find_column(filtered, TERM_COLUMNS)
    if term_column is not None:
        terms = term_series(filtered[term_column])
        filtered = filtered.loc[terms.between(selected_terms[0], selected_terms[1])]

    if selected_high_schools:
        high_school_column = find_column(filtered, HIGH_SCHOOL_COLUMNS)
        if high_school_column is not None:
            allowed = {school.casefold() for school in selected_high_schools}
            mask = filtered[high_school_column].astype(str).str.strip().str.casefold().isin(
                allowed
            )
            filtered = filtered.loc[mask]

    return filtered


def counts_and_rate(frame: pd.DataFrame) -> tuple[float | None, float | None, float | None]:
    """Sum raw counts first, then calculate the overall admit rate."""
    applicant_column = find_column(frame, APPLICANT_COLUMNS)
    admit_column = find_column(frame, ADMIT_COLUMNS)
    applicants = (
        numeric_series(frame[applicant_column]).sum(min_count=1)
        if applicant_column
        else None
    )
    admits = (
        numeric_series(frame[admit_column]).sum(min_count=1)
        if admit_column
        else None
    )
    if applicants is None or pd.isna(applicants):
        applicants = None
    if admits is None or pd.isna(admits):
        admits = None
    rate = admits / applicants if applicants not in (None, 0) and admits is not None else None
    return applicants, admits, rate


def format_count(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.0f}"


def format_rate(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


def chart_palette() -> dict[str, str]:
    """Keep Plotly's embedded charts aligned with the selected app theme."""
    if st.session_state.get("theme_mode") == "Light":
        return {
            "text": "#111827",
            "muted": "#475569",
            "grid": "rgba(15, 23, 42, 0.14)",
            "line": "#111827",
            "secondary": "#64748B",
            "hover": "#FFFFFF",
        }
    return {
        "text": "#F8FAFC",
        "muted": "#B9C2D0",
        "grid": "rgba(255, 255, 255, 0.12)",
        "line": "#FFFFFF",
        "secondary": "#7E8A9F",
        "hover": "#111827",
    }


def style_chart(figure: object) -> object:
    """Apply a high-contrast, transparent dark theme to Plotly figures."""
    palette = chart_palette()
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0, 0, 0, 0)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font={"color": palette["text"], "family": "Google Sans, Arial, sans-serif"},
        title={"font": {"color": palette["text"], "size": 18}},
        legend={
            "font": {"color": palette["text"]},
            "bgcolor": "rgba(0, 0, 0, 0)",
        },
        hoverlabel={
            "bgcolor": palette["hover"],
            "bordercolor": "rgba(255, 255, 255, 0.22)",
            "font": {"color": palette["text"]},
            "namelength": -1,
        },
        hoverdistance=120,
        spikedistance=-1,
        transition={"duration": 550, "easing": "cubic-in-out"},
        margin={"l": 24, "r": 24, "t": 56, "b": 28},
    )
    figure.update_xaxes(
        color=palette["muted"],
        gridcolor=palette["grid"],
        linecolor="rgba(255, 255, 255, 0.18)",
        zerolinecolor=palette["grid"],
        tickfont={"color": palette["muted"]},
        title_font={"color": palette["muted"]},
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1,
        spikecolor="rgba(255, 255, 255, 0.44)",
    )
    figure.update_yaxes(
        color=palette["muted"],
        gridcolor=palette["grid"],
        linecolor="rgba(255, 255, 255, 0.18)",
        zerolinecolor=palette["grid"],
        tickfont={"color": palette["muted"]},
        title_font={"color": palette["muted"]},
    )
    return figure


def render_snapping_trend(figure: object) -> None:
    """Render a point-snapping trend chart with a gently eased hover guide."""
    figure.update_layout(hovermode="closest", hoverdistance=-1)
    figure.update_xaxes(showspikes=False)
    chart_markup = pio.to_html(
        figure,
        full_html=False,
        include_plotlyjs="inline",
        config=CHART_CONFIG,
    )
    components.html(
        f"""
        <style>
            html, body {{
                background: transparent;
                margin: 0;
                overflow: hidden;
                padding: 0;
            }}
            .trend-shell {{
                height: 430px;
                position: relative;
                width: 100%;
            }}
            .trend-shell .plotly-graph-div {{
                height: 100% !important;
                width: 100% !important;
            }}
            .snap-guide {{
                background: rgba(255, 255, 255, 0.64);
                bottom: 39px;
                box-shadow: 0 0 14px rgba(255, 255, 255, 0.24);
                height: auto;
                left: 0;
                opacity: 0;
                pointer-events: none;
                position: absolute;
                top: 58px;
                transform: translate3d(-20px, 0, 0);
                transition: opacity 160ms ease;
                width: 1px;
                z-index: 5;
            }}
        </style>
        <div class="trend-shell">
            {chart_markup}
            <div class="snap-guide" aria-hidden="true"></div>
        </div>
        <script>
        (() => {{
            const shell = document.currentScript.parentElement;
            const guide = shell.querySelector(".snap-guide");
            let graph = null;
            let currentX = -20;
            let targetX = -20;
            let animationFrame = 0;

            const animateGuide = () => {{
                const difference = targetX - currentX;
                currentX += difference * 0.18;
                guide.style.transform = `translate3d(${{currentX}}px, 0, 0)`;
                if (Math.abs(difference) > 0.15) {{
                    animationFrame = requestAnimationFrame(animateGuide);
                }} else {{
                    currentX = targetX;
                    guide.style.transform = `translate3d(${{currentX}}px, 0, 0)`;
                    animationFrame = 0;
                }}
            }};

            const attachHoverMotion = () => {{
                graph = shell.querySelector(".plotly-graph-div");
                if (!graph || !graph._fullLayout || typeof graph.on !== "function") {{
                    window.setTimeout(attachHoverMotion, 80);
                    return;
                }}

                graph.on("plotly_hover", (event) => {{
                    const point = event.points && event.points[0];
                    const axis = graph._fullLayout.xaxis;
                    if (!point || !axis || typeof axis.l2p !== "function") return;
                    targetX = axis._offset + axis.l2p(point.x);
                    guide.style.opacity = "1";
                    if (!animationFrame) animationFrame = requestAnimationFrame(animateGuide);
                }});

                graph.on("plotly_unhover", () => {{
                    guide.style.opacity = "0";
                }});

                new ResizeObserver(() => {{
                    const axis = graph._fullLayout && graph._fullLayout.xaxis;
                    if (axis && typeof axis.l2p === "function" && Number.isFinite(targetX)) {{
                        if (animationFrame) cancelAnimationFrame(animationFrame);
                        animationFrame = 0;
                    }}
                }}).observe(graph);
            }};

            attachHoverMotion();
        }})();
        </script>
        """,
        height=440,
        scrolling=False,
    )


def grouped_rate_frame(
    frame: pd.DataFrame,
    group_column: str,
    output_name: str,
) -> pd.DataFrame:
    """Build weighted rates by group, with a provided-rate fallback for redacted counts."""
    applicant_column = find_column(frame, APPLICANT_COLUMNS)
    admit_column = find_column(frame, ADMIT_COLUMNS)
    provided_rate_column = find_observed_rate_column(frame)
    working = frame.copy()
    working[output_name] = working[group_column].astype(str).str.strip()

    if applicant_column and admit_column:
        working["_applicants"] = numeric_series(working[applicant_column])
        working["_admits"] = numeric_series(working[admit_column])
        grouped = (
            working.groupby(output_name, dropna=False)[["_applicants", "_admits"]]
            .sum(min_count=1)
            .reset_index()
        )
        grouped["Admit Rate"] = grouped["_admits"].div(grouped["_applicants"])
        grouped = grouped.rename(
            columns={"_applicants": "Applicants", "_admits": "Admits"}
        )
        return grouped.dropna(subset=["Admit Rate"])

    if provided_rate_column:
        working["_provided_rate"] = rate_series(working[provided_rate_column])
        grouped = (
            working.groupby(output_name, dropna=False)["_provided_rate"]
            .mean()
            .reset_index()
            .rename(columns={"_provided_rate": "Admit Rate"})
        )
        return grouped.dropna(subset=["Admit Rate"])

    return pd.DataFrame(columns=[output_name, "Admit Rate"])


def ethnicity_count_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Reshape the ethnicity export's count_type/n format into chart-ready counts."""
    ethnicity_column = find_column(frame, ETHNICITY_COLUMNS)
    count_type_column = find_column(frame, ("count_type", "count_kind", "measure"))
    count_column = find_column(frame, ("n", "count", "value", "number"))
    if ethnicity_column is None:
        return pd.DataFrame(columns=["Ethnicity", "Applicants", "Admits"])

    if count_type_column and count_column:
        working = frame.copy()
        working["Ethnicity"] = working[ethnicity_column].astype(str).str.strip()
        working["_count_type"] = (
            working[count_type_column].astype(str).str.strip().str.casefold()
        )
        working["_count"] = numeric_series(working[count_column])
        working = working[working["_count_type"].isin({"app", "adm"})]
        if working.empty:
            return pd.DataFrame(columns=["Ethnicity", "Applicants", "Admits"])

        pivot = (
            working.pivot_table(
                index="Ethnicity",
                columns="_count_type",
                values="_count",
                aggfunc="sum",
            )
            .rename(columns={"app": "Applicants", "adm": "Admits"})
            .reset_index()
        )
        for column in ("Applicants", "Admits"):
            if column not in pivot.columns:
                pivot[column] = pd.NA
        return pivot[["Ethnicity", "Applicants", "Admits"]].dropna(
            subset=["Applicants", "Admits"], how="all"
        )

    applicant_column = find_column(frame, APPLICANT_COLUMNS)
    admit_column = find_column(frame, ADMIT_COLUMNS)
    if applicant_column is None or admit_column is None:
        return pd.DataFrame(columns=["Ethnicity", "Applicants", "Admits"])

    counts = frame.copy()
    counts["Ethnicity"] = counts[ethnicity_column].astype(str).str.strip()
    counts["Applicants"] = numeric_series(counts[applicant_column])
    counts["Admits"] = numeric_series(counts[admit_column])
    return (
        counts.groupby("Ethnicity", dropna=False)[["Applicants", "Admits"]]
        .sum(min_count=1)
        .reset_index()
        .dropna(subset=["Applicants", "Admits"], how="all")
    )


def load_datasets() -> tuple[dict[str, pd.DataFrame], list[str]]:
    loaded: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for key, filename in DATASET_FILES.items():
        frame = load_csv(filename)
        if frame is None:
            missing.append(filename)
        else:
            loaded[key] = frame
    return loaded, missing


st.markdown(
    """
    <div class="hero-kicker">UC system · Bay Area admissions pipeline</div>
    <h1 class="hero-title">UC Admissions Data Explorer</h1>
    <p class="hero-copy">
        Explore how admission outcomes changed across UC campuses and Bay Area high
        schools. Compare observed admit rates with expected rates to see where local
        outcomes outperformed or fell below the modeled baseline.
    </p>
    """,
    unsafe_allow_html=True,
)

datasets, missing_files = load_datasets()

if missing_files:
    st.warning(
        "Some expected data files were not found. Add them to the project root "
        "to unlock the corresponding views: "
        + ", ".join(missing_files)
    )

required_keys = ("modeling", "dashboard", "ethnicity")
missing_required = [DATASET_FILES[key] for key in required_keys if key not in datasets]
if missing_required:
    st.error(
        "The dashboard needs these files before it can calculate the requested "
        "metrics and charts: " + ", ".join(missing_required)
    )
    st.stop()

modeling_data = datasets["modeling"]
dashboard_data = datasets["dashboard"]
ethnicity_data = datasets["ethnicity"]

campus_values = unique_text_values(
    (modeling_data, dashboard_data, ethnicity_data),
    CAMPUS_COLUMNS,
)
campus_options = [SYSTEMWIDE] + [
    value for value in campus_values if not is_systemwide(value)
]
high_school_values = unique_text_values(
    (modeling_data, dashboard_data),
    HIGH_SCHOOL_COLUMNS,
)

term_values: list[int] = []
for frame in (modeling_data, dashboard_data, ethnicity_data):
    term_column = find_column(frame, TERM_COLUMNS)
    if term_column is not None:
        parsed_terms = term_series(frame[term_column]).dropna()
        term_values.extend(parsed_terms.astype(int).tolist())

if term_values:
    min_term, max_term = min(term_values), max(term_values)
else:
    min_term, max_term = 2000, 2025

with st.container(border=True):
    st.markdown('<div class="filter-bar-title">Explore the data</div>', unsafe_allow_html=True)
    filter_columns = st.columns([1.25, 3.3, 2.1, 1.15])
    with filter_columns[0]:
        selected_campus = st.selectbox(
            "UC Campus",
            options=campus_options,
            index=0,
            format_func=lambda value: "Systemwide"
            if value == SYSTEMWIDE
            else campus_label(value),
        )
    with filter_columns[1]:
        selected_high_schools = st.multiselect(
            "High Schools in the Bay Area",
            options=high_school_values,
            help="Leave empty to include all available high schools.",
        )
    with filter_columns[2]:
        selected_terms = st.slider(
            "Fall Terms",
            min_value=min_term,
            max_value=max_term,
            value=(min_term, max_term),
            step=1,
        )
    with filter_columns[3]:
        selected_theme = st.selectbox(
            "Theme",
            options=["Dark", "Light", "System"],
            index=0,
            key="theme_mode",
            help="Choose the dashboard appearance.",
        )
    st.markdown(
        f'<div class="filter-bar-note">{len(modeling_data):,} modeling rows · '
        f'{len(dashboard_data):,} dashboard rows · {selected_theme} theme</div>',
        unsafe_allow_html=True,
    )

if selected_theme == "Light":
    st.markdown(
        """
        <style>
        :root {
            color-scheme: light;
            --app-bg: #F5F7FB;
            --app-text: #111827;
            --app-muted: #475569;
            --app-subtle: #64748B;
            --panel-fill: rgba(255, 255, 255, 0.78);
            --panel-border: rgba(15, 23, 42, 0.13);
            --header-fill: rgba(245, 247, 251, 0.88);
            --grid-line: rgba(15, 23, 42, 0.10);
        }
        .stApp {
            background:
                radial-gradient(circle at 12% 8%, rgba(148, 163, 184, 0.20), transparent 28rem),
                radial-gradient(circle at 86% 18%, rgba(186, 199, 220, 0.22), transparent 26rem),
                var(--app-bg);
        }
        [data-testid="stMetricValue"],
        .hero-title,
        .filter-bar-title {
            color: var(--app-text);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
elif selected_theme == "System":
    st.markdown(
        """
        <style>
        :root {
            color-scheme: light dark;
        }
        @media (prefers-color-scheme: light) {
            :root {
                --app-bg: #F5F7FB;
                --app-text: #111827;
                --app-muted: #475569;
                --app-subtle: #64748B;
                --panel-fill: rgba(255, 255, 255, 0.78);
                --panel-border: rgba(15, 23, 42, 0.13);
                --header-fill: rgba(245, 247, 251, 0.88);
                --grid-line: rgba(15, 23, 42, 0.10);
            }
            .stApp {
                background:
                    radial-gradient(circle at 12% 8%, rgba(148, 163, 184, 0.20), transparent 28rem),
                    radial-gradient(circle at 86% 18%, rgba(186, 199, 220, 0.22), transparent 26rem),
                    var(--app-bg);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

filtered_modeling = filter_frame(
    modeling_data, selected_campus, selected_high_schools, selected_terms
)
filtered_dashboard = filter_frame(
    dashboard_data, selected_campus, selected_high_schools, selected_terms
)
filtered_ethnicity = filter_frame(
    ethnicity_data, selected_campus, selected_high_schools, selected_terms
)

applicants, admits, overall_rate = counts_and_rate(filtered_modeling)
metric_one, metric_two, metric_three = st.columns(3)
with metric_one:
    st.metric("Total Applicants", format_count(applicants))
with metric_two:
    st.metric("Total Admits", format_count(admits))
with metric_three:
    st.metric("Overall Admit Rate", format_rate(overall_rate))

st.divider()

st.subheader("Admit rate trend")
modeling_term_column = find_column(filtered_modeling, TERM_COLUMNS)
if modeling_term_column is None:
    st.info("A Fall Term column is not available in the modeling table.")
else:
    trend_data = filtered_modeling.copy()
    trend_data["_fall_term"] = term_series(trend_data[modeling_term_column])
    trend_data = trend_data.dropna(subset=["_fall_term"])
    if trend_data.empty:
        st.info("No trend data matches the current filters.")
    else:
        trend = grouped_rate_frame(trend_data, "_fall_term", "Fall Term")
        trend["Fall Term"] = trend["Fall Term"].astype(int)
        trend = trend.sort_values("Fall Term")
        if trend.empty:
            st.info(
                "Raw applicant/admit counts or an admit-rate column are needed "
                "to draw the trend."
            )
        else:
            trend_figure = px.line(
                trend,
                x="Fall Term",
                y="Admit Rate",
                markers=True,
                line_shape="spline",
                labels={"Admit Rate": "Admit Rate"},
                title="Observed admit rate by fall term",
            )
            style_chart(trend_figure)
            palette = chart_palette()
            trend_figure.update_traces(
                line={"color": palette["line"], "width": 3},
                marker={
                    "color": palette["line"],
                    "line": {"color": palette["hover"], "width": 1.5},
                    "size": 8,
                },
            )
            trend_figure.update_yaxes(tickformat=".1%", rangemode="tozero")
            render_snapping_trend(trend_figure)

st.subheader("Observed vs. expected by high school")
dashboard_high_school_column = find_column(filtered_dashboard, HIGH_SCHOOL_COLUMNS)
expected_column = find_column(filtered_dashboard, EXPECTED_RATE_COLUMNS)
if dashboard_high_school_column is None:
    st.info("A High School column is not available in dashboard_data.csv.")
elif expected_column is None:
    st.info("An Expected Admit Rate column is not available in dashboard_data.csv.")
else:
    comparison_source = filtered_dashboard.copy()
    comparison_source["_expected_rate"] = rate_series(comparison_source[expected_column])
    comparison = grouped_rate_frame(
        comparison_source,
        dashboard_high_school_column,
        "High School",
    )
    expected_by_school = (
        comparison_source.assign(
            _school=comparison_source[dashboard_high_school_column].astype(str).str.strip()
        )
        .groupby("_school", dropna=False)["_expected_rate"]
        .mean()
        .reset_index()
        .rename(columns={"_school": "High School", "_expected_rate": "Expected Admit Rate"})
    )
    comparison = comparison.merge(expected_by_school, on="High School", how="inner")
    comparison = comparison.sort_values("Admit Rate", ascending=True)
    if comparison.empty:
        st.info("No high-school comparison data matches the current filters.")
    else:
        comparison_long = comparison.melt(
            id_vars=["High School"],
            value_vars=["Admit Rate", "Expected Admit Rate"],
            var_name="Measure",
            value_name="Rate",
        )
        comparison_figure = px.bar(
            comparison_long,
            x="Rate",
            y="High School",
            color="Measure",
            barmode="group",
            orientation="h",
            text="Rate",
            title="Observed and modeled admit rates",
            labels={"Rate": "Admit Rate"},
        )
        style_chart(comparison_figure)
        palette = chart_palette()
        comparison_figure.for_each_trace(
            lambda trace: trace.update(
                marker_color=palette["line"]
                if trace.name == "Admit Rate"
                else palette["secondary"]
            )
        )
        comparison_figure.update_traces(texttemplate="%{text:.1%}", textposition="outside")
        comparison_figure.update_xaxes(tickformat=".1%", range=[0, 1])
        comparison_figure.update_layout(legend_title_text="")
        st.plotly_chart(comparison_figure, config=CHART_CONFIG, width="stretch")

st.subheader("Applicants and admits by ethnicity")
ethnicity_column = find_column(filtered_ethnicity, ETHNICITY_COLUMNS)
if ethnicity_column is None:
    st.info("An Ethnicity column is not available in the ethnicity summary.")
else:
    ethnicity_counts = ethnicity_count_frame(filtered_ethnicity)
    if ethnicity_counts.empty:
        st.info(
            "No applicant and admit counts match the current ethnicity filters."
        )
    else:
        ethnicity_long = ethnicity_counts.melt(
            id_vars=["Ethnicity"],
            value_vars=["Applicants", "Admits"],
            var_name="Measure",
            value_name="Count",
        )
        ethnicity_figure = px.bar(
            ethnicity_long,
            x="Ethnicity",
            y="Count",
            color="Measure",
            barmode="group",
            title="Applicant and admit counts",
            labels={"Count": "People"},
        )
        style_chart(ethnicity_figure)
        palette = chart_palette()
        ethnicity_figure.for_each_trace(
            lambda trace: trace.update(
                marker_color=palette["line"]
                if trace.name == "Applicants"
                else palette["secondary"]
            )
        )
        ethnicity_figure.update_layout(legend_title_text="")
        st.plotly_chart(ethnicity_figure, config=CHART_CONFIG, width="stretch")

st.markdown(
    '<div class="methodology-title">Methodology &amp; Dataset Info</div>',
    unsafe_allow_html=True,
)
with st.container(border=True):
    st.markdown(
        """
        **How rates are computed**

        Admit rates are calculated as **total admits ÷ total applicants**. When
        multiple rows are grouped by fall term, high school, or ethnicity, the
        dashboard sums the raw applicant and admit counts first and divides the
        totals once. This avoids averaging row-level rates and gives larger
        applicant groups the appropriate weight.

        **Dataset coverage**

        The app reads the Bay Area modeling table, dashboard comparison data,
        ethnicity summary, freshman admissions by discipline, and transfer
        admissions by major directly from CSV files. The freshman and transfer
        tables are loaded for dataset coverage and future expansion; the three
        visualizations above use the modeling, dashboard, and ethnicity tables
        respectively.

        **Data redaction**

        UC admissions exports may redact or suppress small counts for privacy.
        Missing, suppressed, or non-numeric values are excluded from the
        corresponding sums and are never treated as zero. Rows without enough
        numeric information to calculate a rate are omitted from that chart.
        """
    )
