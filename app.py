"""
Cell Culture / Exosome Lab Notebook
-----------------------------------
A shareable, editable digital lab notebook built with Streamlit.

Run locally:      streamlit run app.py
Share with lab:    deploy to Streamlit Community Cloud (see README.md)

Data is stored in two plain files next to this script:
  - lab_notebook_data.csv   (every logged entry)
  - lab_notebook_presets.json (editable preset lists, e.g. cell lines)
Both are human-readable and safe to back up, version control, or move.
"""

import json
import os
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# Config / file paths
# ------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "lab_notebook_data.csv")
PRESETS_FILE = os.path.join(APP_DIR, "lab_notebook_presets.json")

COLUMNS = [
    "entry_id",
    "logged_at",
    "cell_line",
    "culture_condition",
    "experiment_setup_date",
    "set_number",
    "total_volume_mL",
    "total_cell_concentration",
    "live_cell_concentration",
    "concentration_multiplier",
    "total_cell_count",
    "live_cell_count",
    "percent_live",
    "seeding_number",
    "exosome_collection_date",
    "exosome_resuspension_volume_mL",
    "exosome_particle_concentration",
    "exosome_concentration_multiplier",
    "exosome_dilution_factor",
    "total_exosome_particles",
    "particles_per_total_cell",
    "particles_per_live_cell",
    "tube_label_internal",
    "tube_label_external",
    "notes",
]

# Human-readable label shown per preset category in the "Manage Presets" tab
PRESET_LABELS = {
    "cell_lines": "Preset cell lines",
    "culture_conditions": "Culture conditions",
}

DEFAULT_PRESETS = {
    "cell_lines": [
        "MaryX",
        "HTB-126",
        "MDA-MB-231",
        "MCF7-WT",
        "MCF7-gCDH1",
        "MB468",
        "MDA-MB-468",
        "T47D",
        "BT549",
    ],
    "culture_conditions": [
        "Monolayer",
        "Induced spheroid",
        "Spontaneous spheroid formation",
    ],
}

# Automated cell counters (Countess, Cellometer, etc.) typically report
# concentration as a raw number that needs multiplying, e.g. "1.2 x10^6/mL".
MULTIPLIER_OPTIONS = {
    "cells/mL (raw number)": 1,
    "×10^3 cells/mL": 1_000,
    "×10^4 cells/mL": 10_000,
    "×10^5 cells/mL": 100_000,
    "×10^6 cells/mL": 1_000_000,
}

# ZetaView (NTA) particle concentrations are typically reported in the
# 10^7 - 10^11 particles/mL range.
EXOSOME_MULTIPLIER_OPTIONS = {
    "particles/mL (raw number)": 1,
    "×10^6 particles/mL": 1_000_000,
    "×10^7 particles/mL": 10_000_000,
    "×10^8 particles/mL": 100_000_000,
    "×10^9 particles/mL": 1_000_000_000,
    "×10^10 particles/mL": 10_000_000_000,
    "×10^11 particles/mL": 100_000_000_000,
}

st.set_page_config(page_title="Lab Notebook", page_icon="🧫", layout="wide")


# ------------------------------------------------------------------
# Persistence helpers
# ------------------------------------------------------------------
def load_presets():
    if os.path.exists(PRESETS_FILE):
        with open(PRESETS_FILE, "r") as f:
            presets = json.load(f)
        # backfill any preset categories added in later versions of the app
        for key, default_values in DEFAULT_PRESETS.items():
            presets.setdefault(key, default_values)
        return presets
    return DEFAULT_PRESETS.copy()


def save_presets(presets):
    with open(PRESETS_FILE, "w") as f:
        json.dump(presets, f, indent=2)


def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE, dtype=str)
        return df
    return pd.DataFrame(columns=COLUMNS)


def save_data(df):
    df.to_csv(DATA_FILE, index=False)


def next_entry_id(df):
    if df.empty:
        return 1
    return int(pd.to_numeric(df["entry_id"], errors="coerce").max()) + 1


if "presets" not in st.session_state:
    st.session_state.presets = load_presets()
if "data" not in st.session_state:
    st.session_state.data = load_data()


# ------------------------------------------------------------------
# Layout
# ------------------------------------------------------------------
st.title("🧫 Cell Culture & Exosome Lab Notebook")
st.caption(
    "Log cell culture setups and exosome collections. "
    "Entries save automatically to a shared CSV file that everyone with "
    "access to this app can view and edit."
)

tab_add, tab_view, tab_presets, tab_sop = st.tabs(
    [
        "➕ Add Entry",
        "📓 Notebook (view / edit)",
        "⚙️ Manage Presets",
        "🧪 Mary-X Exosome SOP",
    ]
)

# ------------------------------------------------------------------
# TAB 1 — Add Entry
# ------------------------------------------------------------------
with tab_add:
    st.subheader("New cell culture / exosome entry")

    presets = st.session_state.presets

    col1, col2 = st.columns(2)

    with col1:
        cell_line_choice = st.selectbox(
            "Cell line (preset)",
            options=presets["cell_lines"] + ["➕ Type a new cell line..."],
            help="Pick from saved cell lines, or choose the last option to enter a new one.",
        )
        if cell_line_choice == "➕ Type a new cell line...":
            cell_line = st.text_input("New cell line name", key="new_cell_line_inline")
        else:
            cell_line = cell_line_choice

        condition_choice = st.selectbox(
            "Culture condition (preset)",
            options=presets["culture_conditions"] + ["➕ Type a new condition..."],
            help="Monolayer, induced spheroid, or spontaneous spheroid formation — or add your own.",
        )
        if condition_choice == "➕ Type a new condition...":
            culture_condition = st.text_input("New culture condition", key="new_condition_inline")
        else:
            culture_condition = condition_choice

        experiment_setup_date = st.date_input("Experimental setup date", value=date.today())
        set_number = st.number_input("Number of set (replicate/set #)", min_value=1, step=1, value=1)
        seeding_number = st.number_input("Seeding number (cells seeded)", min_value=0, step=1000, value=0)
        total_volume_mL = st.number_input(
            "Total volume (mL)",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            help="Total suspension volume — total/live cell counts are calculated from this.",
        )

    with col2:
        st.markdown("**From automated cell counter**")
        multiplier_label = st.selectbox(
            "Concentration units reported by counter",
            options=list(MULTIPLIER_OPTIONS.keys()),
            index=4,  # defaults to x10^6 cells/mL, the common Countess/Cellometer output
        )
        multiplier = MULTIPLIER_OPTIONS[multiplier_label]

        cc1, cc2 = st.columns(2)
        with cc1:
            total_cell_concentration = st.number_input(
                "Total cell concentration", min_value=0.0, step=0.01, format="%.3f"
            )
        with cc2:
            live_cell_concentration = st.number_input(
                "Live cell concentration", min_value=0.0, step=0.01, format="%.3f"
            )

        total_cell_count = round(total_cell_concentration * multiplier * total_volume_mL)
        live_cell_count = round(live_cell_concentration * multiplier * total_volume_mL)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total cell count", f"{total_cell_count:,}")
        m2.metric("Live cell count", f"{live_cell_count:,}")

        if total_cell_count > 0:
            percent_live = round((live_cell_count / total_cell_count) * 100, 2)
            m3.metric("% live cells", f"{percent_live}%")
            if live_cell_concentration > total_cell_concentration:
                st.warning("Live cell concentration is greater than total cell concentration — please double-check.")
        else:
            percent_live = 0.0
            m3.metric("% live cells", "—")

        exosome_collection_date = st.date_input(
            "Date of exosome collection", value=date.today(), key="exo_date"
        )

    st.markdown("---")
    st.markdown("**Exosome quantification (ZetaView / NTA)**")

    ecol1, ecol2 = st.columns(2)
    with ecol1:
        exosome_resuspension_volume_mL = st.number_input(
            "Exosome resuspension volume (mL)",
            min_value=0.0,
            step=0.01,
            format="%.3f",
            help="Final volume the exosome pellet was resuspended in — used with the ZetaView "
            "concentration to get total particles.",
        )
        exosome_dilution_factor = st.number_input(
            "Dilution factor (as run on ZetaView)",
            min_value=1.0,
            step=1.0,
            value=1.0,
            help="If the sample was diluted before reading, enter the dilution factor (e.g. 1000 for a 1:1000 dilution). Leave as 1 if undiluted.",
        )
    with ecol2:
        exosome_multiplier_label = st.selectbox(
            "Concentration units reported by ZetaView",
            options=list(EXOSOME_MULTIPLIER_OPTIONS.keys()),
            index=3,  # defaults to x10^8 particles/mL, a common NTA range
        )
        exosome_multiplier = EXOSOME_MULTIPLIER_OPTIONS[exosome_multiplier_label]
        exosome_particle_concentration = st.number_input(
            "Particle concentration (as read)", min_value=0.0, step=0.01, format="%.3f"
        )

    total_exosome_particles = round(
        exosome_particle_concentration
        * exosome_multiplier
        * exosome_dilution_factor
        * exosome_resuspension_volume_mL
    )

    particles_per_total_cell = (
        round(total_exosome_particles / total_cell_count, 2) if total_cell_count > 0 else 0.0
    )
    particles_per_live_cell = (
        round(total_exosome_particles / live_cell_count, 2) if live_cell_count > 0 else 0.0
    )

    e1, e2, e3 = st.columns(3)
    e1.metric("Total exosome particles", f"{total_exosome_particles:,}")
    e2.metric(
        "Particles / total cell",
        f"{particles_per_total_cell:,.2f}" if total_cell_count > 0 else "—",
    )
    e3.metric(
        "Particles / live cell",
        f"{particles_per_live_cell:,.2f}" if live_cell_count > 0 else "—",
    )
    if total_exosome_particles > 0 and total_cell_count == 0:
        st.info("Enter cell counter values above to calculate particles per cell.")

    st.markdown("---")
    st.markdown("**Sample tube labels** (two separate labels — auto-suggested, fully editable)")

    CONDITION_ABBREVIATIONS = {
        "Monolayer": "ML",
        "Induced spheroid": "IS",
        "Spontaneous spheroid formation": "SS",
    }
    condition_code = CONDITION_ABBREVIATIONS.get(
        culture_condition,
        "".join(w[0] for w in culture_condition.split()[:3]).upper() if culture_condition else "COND",
    )
    suggested_base = (
        f"{cell_line or 'CELLLINE'}_{condition_code}_"
        f"{experiment_setup_date.strftime('%Y%m%d')}_S{int(set_number)}"
    )

    lcol, rcol = st.columns(2)
    with lcol:
        tube_label_internal = st.text_input(
            "Internal / endosomal vesicle — tube label",
            value=f"{suggested_base}_INT",
        )
    with rcol:
        tube_label_external = st.text_input(
            "External exosome — tube label",
            value=f"{suggested_base}_EXT",
        )

    st.markdown("---")
    notes = st.text_area("Free text notes", placeholder="Anything else worth recording about this entry...")

    if st.button("💾 Save entry", type="primary"):
        if not cell_line:
            st.error("Please enter or select a cell line before saving.")
        else:
            df = st.session_state.data
            new_row = {
                "entry_id": next_entry_id(df),
                "logged_at": datetime.now().isoformat(timespec="seconds"),
                "cell_line": cell_line,
                "culture_condition": culture_condition,
                "experiment_setup_date": experiment_setup_date.isoformat(),
                "set_number": int(set_number),
                "total_volume_mL": total_volume_mL,
                "total_cell_concentration": total_cell_concentration,
                "live_cell_concentration": live_cell_concentration,
                "concentration_multiplier": multiplier,
                "total_cell_count": int(total_cell_count),
                "live_cell_count": int(live_cell_count),
                "percent_live": percent_live,
                "seeding_number": int(seeding_number),
                "exosome_collection_date": exosome_collection_date.isoformat(),
                "exosome_resuspension_volume_mL": exosome_resuspension_volume_mL,
                "exosome_particle_concentration": exosome_particle_concentration,
                "exosome_concentration_multiplier": exosome_multiplier,
                "exosome_dilution_factor": exosome_dilution_factor,
                "total_exosome_particles": int(total_exosome_particles),
                "particles_per_total_cell": particles_per_total_cell,
                "particles_per_live_cell": particles_per_live_cell,
                "tube_label_internal": tube_label_internal,
                "tube_label_external": tube_label_external,
                "notes": notes,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.session_state.data = df
            save_data(df)

            # remember new cell line / condition as presets for next time
            if cell_line not in presets["cell_lines"]:
                presets["cell_lines"].append(cell_line)
            if culture_condition and culture_condition not in presets["culture_conditions"]:
                presets["culture_conditions"].append(culture_condition)
            save_presets(presets)
            st.session_state.presets = presets

            st.success(f"Entry #{new_row['entry_id']} saved.")
            st.rerun()

# ------------------------------------------------------------------
# TAB 2 — View / Edit Notebook
# ------------------------------------------------------------------
with tab_view:
    st.subheader("All logged entries")
    df = st.session_state.data.copy()

    if df.empty:
        st.info("No entries yet — add one from the 'Add Entry' tab.")
    else:
        # --- filters ---
        fcol1, fcol2, fcol3 = st.columns([1, 1, 2])
        with fcol1:
            filter_cell_line = st.multiselect(
                "Filter by cell line", options=sorted(df["cell_line"].dropna().unique())
            )
        with fcol2:
            filter_condition = st.multiselect(
                "Filter by culture condition",
                options=sorted(df["culture_condition"].dropna().unique()),
            )
        with fcol3:
            search_text = st.text_input("Search notes / tube labels")

        view_df = df.copy()
        if filter_cell_line:
            view_df = view_df[view_df["cell_line"].isin(filter_cell_line)]
        if filter_condition:
            view_df = view_df[view_df["culture_condition"].isin(filter_condition)]
        if search_text:
            mask = (
                view_df["notes"].fillna("").str.contains(search_text, case=False)
                | view_df["tube_label_internal"].fillna("").str.contains(search_text, case=False)
                | view_df["tube_label_external"].fillna("").str.contains(search_text, case=False)
            )
            view_df = view_df[mask]

        st.caption("Double-click any cell to edit directly. Click 'Save changes' when done.")
        edited_df = st.data_editor(
            view_df,
            num_rows="dynamic",
            width="stretch",
            key="notebook_editor",
            column_config={
                "entry_id": st.column_config.NumberColumn("ID", disabled=True),
                "logged_at": st.column_config.TextColumn("Logged at", disabled=True),
                "percent_live": st.column_config.NumberColumn("% live", format="%.2f%%"),
                "total_cell_count": st.column_config.NumberColumn("Total cells", format="%d"),
                "live_cell_count": st.column_config.NumberColumn("Live cells", format="%d"),
                "total_exosome_particles": st.column_config.NumberColumn("Total exosome particles", format="%d"),
                "particles_per_total_cell": st.column_config.NumberColumn("Particles/total cell", format="%.2f"),
                "particles_per_live_cell": st.column_config.NumberColumn("Particles/live cell", format="%.2f"),
            },
        )

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if st.button("💾 Save changes to notebook"):
                # merge edited rows back into the full dataset by entry_id
                full_df = st.session_state.data.set_index("entry_id")
                edits = edited_df.set_index("entry_id")
                full_df.update(edits)
                # handle any newly added rows (no matching entry_id yet)
                new_rows = edits[~edits.index.isin(full_df.index)]
                full_df = pd.concat([full_df, new_rows])
                full_df = full_df.reset_index()
                st.session_state.data = full_df
                save_data(full_df)
                st.success("Changes saved.")
                st.rerun()
        with bcol2:
            st.download_button(
                "⬇️ Download notebook as CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name=f"lab_notebook_export_{date.today().isoformat()}.csv",
                mime="text/csv",
            )

        st.markdown("---")
        st.subheader("📊 Exosome particles per cell")

        chart_df = view_df.copy()
        chart_df["particles_per_total_cell"] = pd.to_numeric(
            chart_df["particles_per_total_cell"], errors="coerce"
        )
        chart_df["particles_per_live_cell"] = pd.to_numeric(
            chart_df["particles_per_live_cell"], errors="coerce"
        )
        chart_df = chart_df[chart_df["particles_per_total_cell"].fillna(0) > 0]

        if chart_df.empty:
            st.info("No entries with exosome particle data yet — fill in the ZetaView fields on the 'Add Entry' tab.")
        else:
            ccol1, ccol2 = st.columns(2)
            with ccol1:
                metric = st.radio(
                    "Metric",
                    options=["Particles per total cell", "Particles per live cell"],
                    horizontal=True,
                )
            with ccol2:
                color_by_label = st.radio(
                    "Color by", options=["Cell line", "Culture condition"], horizontal=True
                )
            metric_col = (
                "particles_per_total_cell"
                if metric == "Particles per total cell"
                else "particles_per_live_cell"
            )
            color_col = "cell_line" if color_by_label == "Cell line" else "culture_condition"

            chart_df = chart_df.sort_values("experiment_setup_date")
            chart_df["entry_label"] = (
                chart_df["cell_line"] + " · " + chart_df["culture_condition"].fillna("—")
                + " · set " + chart_df["set_number"].astype(str)
                + " · " + chart_df["experiment_setup_date"]
            )

            fig = px.bar(
                chart_df,
                x="entry_label",
                y=metric_col,
                color=color_col,
                labels={
                    "entry_label": "Entry",
                    metric_col: metric,
                    "cell_line": "Cell line",
                    "culture_condition": "Culture condition",
                },
            )
            fig.update_layout(xaxis_tickangle=-30, margin=dict(t=10))
            st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------
# TAB 3 — Manage Presets
# ------------------------------------------------------------------
with tab_presets:
    st.caption("These appear as dropdown options on the 'Add Entry' tab.")
    presets = st.session_state.presets

    for category, label in PRESET_LABELS.items():
        st.subheader(label)
        for item in list(presets[category]):
            c1, c2 = st.columns([4, 1])
            c1.write(item)
            if c2.button("Remove", key=f"remove_{category}_{item}"):
                presets[category].remove(item)
                save_presets(presets)
                st.session_state.presets = presets
                st.rerun()

        new_item = st.text_input(f"Add a new {label.lower()[:-1] if label.endswith('s') else label.lower()}", key=f"new_{category}")
        if st.button("Add preset", key=f"add_{category}"):
            if new_item and new_item not in presets[category]:
                presets[category].append(new_item)
                save_presets(presets)
                st.session_state.presets = presets
                st.success(f"Added '{new_item}'.")
                st.rerun()
        st.markdown("---")



# ------------------------------------------------------------------
# TAB 4 — Mary-X Exosome SOP
# ------------------------------------------------------------------
with tab_sop:
    st.header("🧪 Mary-X spheroid EV collection SOP")
    st.caption(
        "External small-EV collection from conditioned medium and intracellular/endosomal "
        "vesicle collection after trypsin dissociation of Mary-X spheroids."
    )

    st.info(
        "Terminology: the extracellular preparation is best described as a small extracellular "
        "vesicle (EV)-enriched fraction unless exosome biogenesis is demonstrated. The intracellular "
        "preparation is an intracellular/endosomal vesicle-enriched fraction, not released exosomes."
    )

    sop_text = r"""
MARY-X SPHEROID EXTRACELLULAR EV AND INTRACELLULAR/ENDOSOMAL VESICLE COLLECTION SOP

SOP No.: EV-MARYX-001
Version: 1.0
Application: Mary-X inflammatory breast cancer spheroid cultures

1. PURPOSE
To collect (A) extracellular small-EV-enriched material released by Mary-X spheroids into conditioned medium and (B) intracellular/endosomal vesicle-enriched material from Mary-X spheroids following trypsin-mediated dissociation and controlled cell disruption.

2. KEY PRINCIPLES
- Keep extracellular and intracellular fractions separate throughout the workflow.
- Use EV-depleted serum or a validated short serum-free collection condition.
- Process an equal volume of unconditioned collection medium as a background control.
- Record spheroid number/size, viable cell number, collection volume, collection duration, treatment, and viability.
- Report centrifugation force as x g (RCF), not rpm alone.
- Trypsin is used to dissociate Mary-X spheroids; it is not the intracellular-vesicle isolation reagent.

3. MATERIALS
- Mary-X spheroid cultures
- Appropriate growth/collection medium
- EV-depleted FBS if serum is required
- Sterile Ca2+/Mg2+-free PBS
- Trypsin-EDTA
- Complete medium or validated trypsin-neutralization reagent
- Ice-cold isotonic homogenization buffer (example: 250 mM sucrose, 20 mM HEPES, approximately pH 7.4)
- Protease inhibitor cocktail; phosphatase inhibitors if needed
- Refrigerated centrifuge and, if used, ultracentrifuge with appropriate rotor
- Low-protein-binding tubes
- 0.22-micron filter when appropriate for the selected workflow
- NTA/ZetaView, TEM/cryo-EM, and immunoblotting capability as available

4. SAMPLE SET
Prepare, where possible:
- Mary-X conditioned medium: external EV fraction
- Mary-X spheroids/cells: intracellular/endosomal vesicle fraction
- Unconditioned collection medium: process/background control
- Whole-cell lysate: cellular marker control
- EV-depleted post-isolation supernatant: soluble/non-EV comparison

PART A — EXTERNAL EV COLLECTION

5. PREPARE SPHEROIDS FOR COLLECTION
5.1 Grow Mary-X spheroids under validated laboratory culture conditions.
5.2 Use comparable culture age, spheroid number, spheroid size, treatment condition, and collection volume across groups.
5.3 Allow spheroids to settle or use gentle low-speed centrifugation. Avoid mechanical disruption.
5.4 Remove growth medium.
5.5 Wash spheroids gently with PBS twice to reduce residual serum-derived particles.
5.6 Add fresh EV-collection medium and document start time/conditions.

6. COLLECT CONDITIONED MEDIUM
6.1 Transfer conditioned medium without intentionally collecting spheroids.
6.2 Centrifuge at 300 x g for 10 min at 4 C. Transfer supernatant.
6.3 Centrifuge at 2,000 x g for 10-20 min at 4 C. Transfer supernatant.
6.4 Centrifuge at 10,000 x g for approximately 30 min at 4 C. Transfer supernatant carefully.
6.5 Retain the 10,000 x g pellet separately only if large-EV analysis is planned.

7. SMALL-EV ENRICHMENT
Option A — Differential ultracentrifugation
7.1 Transfer clarified conditioned medium to compatible ultracentrifuge tubes and balance according to rotor requirements.
7.2 Centrifuge at approximately 100,000 x g for 70-120 min at 4 C.
7.3 Carefully remove supernatant.
7.4 Gently resuspend the pellet in cold PBS.
7.5 For improved purity, wash by repeating approximately 100,000 x g for 70-120 min at 4 C.
7.6 Resuspend the final pellet in a small, recorded volume of sterile PBS or appropriate assay buffer.

Option B — Size-exclusion chromatography (SEC)
7.1 After the 10,000 x g clarification step, concentrate conditioned medium if required by the validated column workflow.
7.2 Load the sample onto a validated SEC column.
7.3 Collect sequential fractions and identify EV-enriched fractions according to laboratory/column validation.
7.4 Pool EV-enriched fractions and concentrate if required.

PART B — INTRACELLULAR/ENDOSOMAL VESICLE COLLECTION

8. HARVEST MARY-X SPHEROIDS
8.1 After conditioned-medium removal, collect spheroids into a separate tube.
8.2 Wash with cold PBS three times to minimize carryover of extracellular EVs.

9. TRYPSIN DISSOCIATION
9.1 Remove PBS completely.
9.2 Add the minimum sufficient volume of trypsin-EDTA to cover the spheroid pellet.
9.3 Incubate under the laboratory's validated Mary-X dissociation conditions while monitoring microscopically.
9.4 Use gentle pipetting as needed to obtain a single-cell or small-cluster suspension; avoid excessive trituration.
9.5 Stop trypsinization promptly when adequate dissociation is achieved.
9.6 Neutralize trypsin immediately with complete medium or a validated neutralizing reagent.

10. REMOVE RESIDUAL TRYPSIN AND EXTRACELLULAR MATERIAL
10.1 Centrifuge cells at approximately 300-500 x g for 5 min at 4 C.
10.2 Discard supernatant and resuspend cells in cold PBS.
10.3 Repeat PBS washing 2-3 times.
10.4 Record viable and total cell counts and percent viability.
10.5 Normalize starting material to viable cell number where possible.

11. CONTROLLED CELL DISRUPTION
11.1 Resuspend washed cells in ice-cold isotonic homogenization buffer containing fresh protease inhibitors.
11.2 Keep the sample on ice.
11.3 Disrupt cells using a validated gentle mechanical method such as Dounce homogenization.
11.4 The goal is plasma-membrane disruption while preserving intracellular membrane-bound vesicles.
11.5 Avoid aggressive sonication when intact vesicles are required.

12. DIFFERENTIAL CENTRIFUGATION OF THE INTRACELLULAR FRACTION
12.1 Centrifuge homogenate at approximately 500-1,000 x g for 10 min at 4 C to remove intact cells/nuclei. Transfer supernatant.
12.2 Centrifuge supernatant at approximately 10,000 x g for 20-30 min at 4 C to remove large organelles/debris. Transfer supernatant.
12.3 Ultracentrifuge the resulting supernatant at approximately 100,000 x g for 70-120 min at 4 C.
12.4 Remove supernatant carefully.
12.5 Gently resuspend the pellet in cold PBS or isotonic buffer.
12.6 Repeat approximately 100,000 x g for 70-120 min at 4 C as a wash if appropriate.
12.7 Resuspend the final pellet and label it: Mary-X intracellular/endosomal vesicle-enriched fraction.

13. STORAGE
- Proceed directly to characterization whenever possible.
- Keep samples on ice during short-term processing.
- For longer storage, aliquot into low-protein-binding tubes using the laboratory's validated EV storage temperature.
- Avoid unnecessary freeze-thaw cycles and keep storage history equivalent across experimental groups.

14. CHARACTERIZATION
Use complementary methods rather than a single marker.
Particle analysis: NTA/ZetaView or an equivalent validated method. Record concentration, size distribution, dilution, and instrument settings.
Morphology: TEM or cryo-EM where available.
EV-associated proteins: use multiple markers such as CD9, CD63, CD81, TSG101, and ALIX, selected according to the biological question and laboratory validation.
Assess cellular contamination markers where appropriate. Interpret intracellular fractions differently because organellar markers may legitimately be present.

15. TRYPSIN-SPECIFIC CONTROL
Because trypsin is a protease, record trypsin concentration, exposure duration, temperature, and neutralization method. Keep these parameters identical among groups. Prolonged exposure can alter membrane proteins and viability. Do not expose the extracellular EV preparation to trypsin unless the experiment specifically requires a protease-accessibility assay.

16. NORMALIZATION
External EV fraction:
- particles/mL conditioned medium
- particles/10^6 viable cells
- EV-associated protein/10^6 viable cells
- particles/spheroid when spheroid number is standardized

Intracellular/endosomal fraction:
- particles/10^6 viable cells
- vesicle-associated protein/10^6 viable cells

17. QUALITY-CONTROL CHECKLIST
- Comparable spheroid viability among groups
- Equivalent starting material or defined normalization
- Unconditioned-medium control processed in parallel
- Multiple EV-associated markers assessed
- Major cellular contamination assessed for extracellular EVs
- External and intracellular fractions never combined
- Trypsin conditions documented and consistent
- Rotor and RCF documented for each centrifugation step
- Equivalent storage and freeze-thaw history among samples

18. DATA TO RECORD
Mary-X passage/identifier; treatment; spheroid number; approximate spheroid size; total and viable cell number; percent viability; medium formulation; EV-depleted-serum lot; conditioned-medium volume; collection duration; trypsin concentration and exposure time; centrifuge and rotor; RCF; temperature; final resuspension volume; storage conditions; freeze-thaw cycles; particle concentration; size distribution; protein concentration; EV markers; contamination markers.
"""

    with st.expander("📌 Purpose, terminology & experimental design", expanded=True):
        st.markdown(
            """
### Purpose
Collect two **separate** preparations from Mary-X spheroids:
1. **External small-EV-enriched fraction** from conditioned medium.
2. **Intracellular/endosomal vesicle-enriched fraction** after trypsin dissociation and controlled cell disruption.

### Core controls
- Unconditioned collection medium processed in parallel.
- Whole-cell lysate.
- Viability measurement at harvest.
- Matched collection volume, duration, rotor/RCF, and storage conditions.
            """
        )

    with st.expander("A — External EV collection from conditioned medium", expanded=True):
        st.markdown(
            """
1. Grow comparable Mary-X spheroids and switch to validated EV-collection medium.
2. Wash spheroids gently with PBS **2×** before starting the collection period.
3. Collect conditioned medium without aspirating spheroids.
4. **300 × g, 10 min, 4 °C** → transfer supernatant.
5. **2,000 × g, 10–20 min, 4 °C** → transfer supernatant.
6. **10,000 × g, ~30 min, 4 °C** → transfer supernatant.
7. Enrich small EVs using either:
   - **~100,000 × g, 70–120 min, 4 °C**, followed by a PBS wash and repeat ultracentrifugation, or
   - a validated **size-exclusion chromatography (SEC)** workflow.
8. Resuspend in a recorded final volume and proceed to characterization.
            """
        )

    with st.expander("B — Intracellular/endosomal vesicle collection using trypsin", expanded=True):
        st.markdown(
            """
1. Collect the Mary-X spheroids **after external conditioned medium has been removed**.
2. Wash spheroids with cold PBS **3×**.
3. Add the minimum sufficient amount of **trypsin-EDTA** and monitor dissociation microscopically.
4. Use gentle pipetting; stop as soon as an acceptable single-cell/small-cluster suspension is obtained.
5. Neutralize trypsin immediately.
6. Pellet cells at **~300–500 × g for 5 min at 4 °C** and wash with cold PBS **2–3×**.
7. Count total/viable cells and record viability.
8. Resuspend cells in ice-cold isotonic homogenization buffer plus protease inhibitors.
9. Disrupt cells gently (for example, validated Dounce homogenization). Avoid aggressive sonication if intact vesicles are required.
10. **~500–1,000 × g, 10 min, 4 °C** → remove intact cells/nuclei.
11. **~10,000 × g, 20–30 min, 4 °C** → remove large organelles/debris.
12. **~100,000 × g, 70–120 min, 4 °C** → enrich the small intracellular/endosomal vesicle fraction.
13. Wash and repeat ultracentrifugation if appropriate, then resuspend in a recorded final volume.
            """
        )

    with st.expander("🧬 Characterization, normalization & QC"):
        st.markdown(
            """
**Characterization**
- NTA/ZetaView: concentration and size distribution.
- TEM/cryo-EM where available.
- Multiple EV-associated markers such as **CD9, CD63, CD81, TSG101, and ALIX**.
- Appropriate contamination markers for extracellular preparations.

**Normalization**
- External: particles/mL conditioned medium, particles/10⁶ viable cells, and optionally particles/spheroid.
- Intracellular/endosomal: particles/10⁶ viable cells and/or vesicle-associated protein/10⁶ viable cells.

**Trypsin QC**
Record trypsin concentration, exposure time, temperature, and neutralization method. Keep these parameters identical across groups because prolonged protease exposure can affect viability and surface proteins.
            """
        )

    with st.expander("📝 Required experiment record"):
        st.markdown(
            """
Record: Mary-X passage/identifier, treatment, spheroid number and approximate size, total/live cell counts, viability, medium formulation, EV-depleted-serum lot, conditioned-medium volume, collection duration, trypsin conditions, centrifuge/rotor, RCF, temperature, final resuspension volume, storage conditions, freeze-thaw cycles, NTA results, protein concentration, EV markers, and contamination markers.
            """
        )

    st.download_button(
        "⬇️ Download Mary-X SOP as TXT",
        data=sop_text.encode("utf-8"),
        file_name="MaryX_EV_collection_SOP.txt",
        mime="text/plain",
    )
