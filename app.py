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

MARYX_SOP_VERSION = "1.7"
MARYX_SOP_UPDATED = "2026-10-07"
MARYX_SOP_SOURCE = "Mary-X spheroid culture protocol.docx"
MARYX_SOP_NOTES = """
**Source and scope:** Spheroid handling and reseeding are adapted from the
supplied Mary-X spheroid culture protocol. The culture medium and incubation
duration follow the researcher's clarification: **DMEM with 10% exosome-depleted
FBS and Antibiotic-Antimycotic (Anti-Anti), incubated for 5 days**. The
conditioned-medium debris-clearing step is **2,000 × g for 15 minutes at 4 °C**.
The subsequent EV enrichment and separate intracellular workflow are carried
forward from the earlier SOP; they are not specified in the culture document.
Trypsin incubation, vortexing, pipetting, neutralization, and cell-counting
instructions incorporate the researcher's subsequent clarifications.

**Culture conditions:** Incubate at **37 °C, 5% CO₂ for 5 days** in the
reported DMEM-based medium. Record the Anti-Anti product, stock strength,
added volume, and final concentration; its concentration was not supplied.

**Fraction identity:** Conditioned-medium EVs, EVs trapped between spheroid
cells, and intracellular vesicles are different sample types. This SOP covers
conditioned-medium EVs and the earlier separate intracellular preparation.
The intracellular workflow does not isolate spheroid-trapped extracellular EVs.
""".strip()

MARYX_SAMPLE_SUMMARY = """
## Two samples and storage

| Sample label | Source and preparation | Storage |
| --- | --- | --- |
| **1. Internal exosome (INT)** | Reserved spheroid aliquot; trypsin dissociation, neutralization, washing, automated cell counting with trypan blue, then the intracellular preparation described below. | Separate labeled aliquots at **−80 °C**. |
| **2. External exosomes (EXT)** | Conditioned medium; clarification, EV enrichment, and final resuspension. | Separate labeled aliquots at **−80 °C**. |

These are the researcher's sample labels. In this SOP, the internal sample is
an intracellular membrane/vesicle-enriched preparation, and the external sample
is a conditioned-medium EV-enriched preparation. Keep the two samples separate.
Record the experiment ID, sample type, collection date, aliquot volume, and
freezer/rack/box/position for each stored tube.
""".strip()

# Embedded SVG keeps the diagram self-contained without another Python package.
MARYX_SAMPLE_DIAGRAM_SVG = """<svg xmlns="http://www.w3.org/2000/svg"
    width="860" height="786" viewBox="0 0 860 786"
    role="img" aria-labelledby="maryx-title maryx-description">
  <title id="maryx-title">Mary-X two-sample workflow and storage</title>
  <desc id="maryx-description">After the five-day Mary-X culture, process the
    reserved spheroids for sample 1, Internal exosome, and conditioned medium
    for sample 2, External exosomes. Keep the two preparations in separate
    labeled aliquots and store both at minus 80 degrees Celsius.</desc>
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5"
        orient="auto" markerUnits="userSpaceOnUse">
      <path d="M0,0 L10,5 L0,10 Z" fill="#53627a"/>
    </marker>
  </defs>
  <rect width="860" height="786" fill="#ffffff"/>
  <g font-family="Arial, DejaVu Sans, sans-serif" text-anchor="middle" fill="#172b44">
    <text x="430" y="39" font-size="27" font-weight="700">Mary-X two-sample workflow</text>
    <text x="430" y="68" font-size="18" fill="#526276">Two separately labeled preparations</text>

    <rect x="125" y="94" width="610" height="94" rx="12"
        fill="#f2f5f9" stroke="#b8c3d1" stroke-width="1.5"/>
    <text x="430" y="125" font-size="23" font-weight="700">Mary-X spheroids and conditioned medium</text>
    <text x="430" y="151" font-size="17">DMEM + 10% exosome-depleted FBS + Anti-Anti</text>
    <text x="430" y="175" font-size="17">5 days at 37 °C, 5% CO₂</text>

    <path d="M430,188 V212 H215 V235" fill="none" stroke="#53627a"
        stroke-width="2.5" marker-end="url(#arrow)"/>
    <path d="M430,212 H645 V235" fill="none" stroke="#53627a"
        stroke-width="2.5" marker-end="url(#arrow)"/>

    <rect x="35" y="242" width="360" height="88" rx="10"
        fill="#f1f4ff" stroke="#637bb3" stroke-width="1.5"/>
    <text x="215" y="276" font-size="23" font-weight="700">Retained spheroids</text>
    <text x="215" y="305" font-size="17">Reserved aliquot for internal preparation</text>

    <rect x="465" y="242" width="360" height="88" rx="10"
        fill="#edf8f5" stroke="#318978" stroke-width="1.5"/>
    <text x="645" y="276" font-size="23" font-weight="700">Conditioned medium</text>
    <text x="645" y="305" font-size="17">Supernatant for external EV preparation</text>

    <path d="M215,330 V353" fill="none" stroke="#53627a" stroke-width="2.5"
        marker-end="url(#arrow)"/>
    <path d="M645,330 V353" fill="none" stroke="#53627a" stroke-width="2.5"
        marker-end="url(#arrow)"/>

    <rect x="35" y="360" width="360" height="132" rx="10"
        fill="#ffffff" stroke="#637bb3" stroke-width="1.5"/>
    <text x="215" y="394" font-size="21" font-weight="700">Trypsin dissociation</text>
    <text x="215" y="424" font-size="18">Neutralize, wash, and count cells</text>
    <text x="215" y="452" font-size="18">Intracellular vesicle preparation</text>
    <text x="215" y="477" font-size="16" fill="#526276">Follow the separate intracellular workflow</text>

    <rect x="465" y="360" width="360" height="132" rx="10"
        fill="#ffffff" stroke="#318978" stroke-width="1.5"/>
    <text x="645" y="394" font-size="21" font-weight="700">Clarify conditioned medium</text>
    <text x="645" y="424" font-size="18">Includes 2,000 × g, 15 min, 4 °C</text>
    <text x="645" y="452" font-size="18">EV enrichment and resuspension</text>
    <text x="645" y="477" font-size="16" fill="#526276">Follow the external EV workflow</text>

    <path d="M215,492 V515" fill="none" stroke="#53627a" stroke-width="2.5"
        marker-end="url(#arrow)"/>
    <path d="M645,492 V515" fill="none" stroke="#53627a" stroke-width="2.5"
        marker-end="url(#arrow)"/>

    <rect x="35" y="522" width="360" height="186" rx="12"
        fill="#eef2ff" stroke="#49669e" stroke-width="2"/>
    <text x="215" y="562" font-size="25" font-weight="700">1. Internal exosome</text>
    <text x="215" y="594" font-size="18">INT · separate labeled aliquots</text>
    <text x="215" y="656" font-size="43" font-weight="700">−80 °C</text>
    <text x="215" y="689" font-size="17">Storage temperature</text>

    <rect x="465" y="522" width="360" height="186" rx="12"
        fill="#e7f5ef" stroke="#257564" stroke-width="2"/>
    <text x="645" y="562" font-size="25" font-weight="700">2. External exosomes</text>
    <text x="645" y="594" font-size="18">EXT · separate labeled aliquots</text>
    <text x="645" y="656" font-size="43" font-weight="700">−80 °C</text>
    <text x="645" y="689" font-size="17">Storage temperature</text>

    <text x="430" y="745" font-size="17">Label each tube with experiment ID, sample type, date, and aliquot volume.</text>
    <text x="430" y="773" font-size="16" fill="#526276">Record freezer / rack / box / position and freeze–thaw history.</text>
  </g>
</svg>"""

# The screen and TXT download use the same sections so protocol changes stay in sync.
MARYX_SOP_SECTIONS = [
    (
        "Day 0 — Spheroid preparation and 5-day incubation",
        """
1. Inspect comparable Mary-X spheroids under the microscope. Record size,
   compactness, debris, and contamination status. Use healthy, compact spheroids
   and record the medium formulation, passage, starting material, and viability.
2. Gently collect spheroids plus medium into a sterile 15 mL conical tube using
   a wide-bore or cut pipette tip. Avoid breaking the spheroids. Use appropriately
   sized vessels if the total volume exceeds the tube's working capacity.
3. Rinse the original dish with **1–2 mL fresh DMEM containing 10%
   exosome-depleted FBS and Anti-Anti**, gently swirl, and transfer the remaining
   spheroids into the same collection tube. Use the laboratory's established
   Anti-Anti concentration and record it.
4. Centrifuge at **100 × g for 5 minutes at room temperature, with no brake**.
5. Carefully remove the supernatant, leaving approximately **100–300 µL**
   above the loose spheroid pellet to avoid losing spheroids.
6. Perform the PBS wash specified in the source: gently resuspend in
   **5–10 mL sterile PBS**, then centrifuge at **100 × g for 5 minutes at
   room temperature, with no brake**. Remove the wash carefully. The source
   specifies one PBS wash cycle, replacing the earlier generic PBS 2× instruction.
7. Resuspend in **15 mL fresh DMEM containing 10% exosome-depleted FBS and
   Anti-Anti**, prewarmed to **37 °C**. Gently flick or pipette **1–3 times**
   with a wide-bore tip; do not vortex. Use the appropriate culture vessel.
   The 15 mL starting volume is carried forward from the supplied culture file;
   record the actual volume used.
8. Incubate at **37 °C, 5% CO₂ for 5 days**. Record the actual start and end
   dates/times, medium and supplement lots, Anti-Anti final concentration,
   spheroid morphology, and viability. Document any medium additions or
   changes during incubation so the conditioned-medium collection interval
   can be interpreted correctly.
""".strip(),
    ),
    (
        "After 5 days — Conditioned-medium harvest and spheroid recovery",
        """
1. At the end of the **5-day incubation**, gently collect the spheroid
   suspension using a wide-bore or cut pipette tip. Avoid disrupting spheroids
   and use a tube suitable for the collection volume.
2. Centrifuge at **100 × g for 5 minutes at room temperature, with no brake**.
3. Carefully transfer the **supernatant** into a separate clean tube for the
   external EV workflow. Avoid transferring the spheroid pellet. Record the
   actual recovered conditioned-medium volume; keep the EV sample cold during
   the subsequent processing steps.
4. For continued culture, prepare fresh **DMEM with 10% exosome-depleted FBS
   and Anti-Anti** at the recorded laboratory concentration. Gently resuspend
   the retained spheroids in **5 mL** of this medium and transfer into a new
   **T-75 flask containing 10 mL** of the same fresh medium. Rinse the collection
   tube with **2 mL** of the same medium and add the rinse to the flask.
5. Incubate at **37 °C, 5% CO₂** and avoid moving the flask for several hours.
   Record passage/split ratio, spheroid number or approximate density, medium
   volume, vessel, centrifugation conditions, and post-reseeding morphology.

Keep all fresh recovery medium out of the harvested EV sample. If an
intracellular preparation is planned, reserve a separate, recorded spheroid
aliquot before adding recovery medium; that aliquot follows the intracellular
workflow below instead of the reseeding steps.

The source advises against trypsinizing spheroids unless single-cell
dissociation is the goal. Record recovery status and the start of each
subsequent collection cycle separately.
""".strip(),
    ),
    (
        "External EVs — Medium clarification and small-EV enrichment",
        """
Start with the conditioned-medium supernatant saved after the **5-day
incubation** and **100 × g** spheroid-harvest spin. The following spins process that medium,
not the intact spheroid pellet.

1. Centrifuge at **300 × g for 10 minutes at 4 °C** to remove residual cells.
   Transfer the supernatant into a clean tube without disturbing the pellet.
2. Centrifuge at **2,000 × g for 15 minutes at 4 °C**. Transfer the supernatant
   into a clean tube without disturbing the debris pellet.
3. Centrifuge at **10,000 × g for approximately 30 minutes at 4 °C**.
   Transfer the supernatant carefully. Keep the large-particle/large-EV pellet
   separate if it is being retained for analysis.
4. Enrich small EVs using one laboratory-validated method:
   - **Ultracentrifugation:** approximately **100,000 × g for 70–120 minutes
     at 4 °C**. Recover the pellet, gently resuspend it in cold PBS, fill the
     approved ultracentrifuge tube as required, and repeat approximately
     **100,000 × g for 70–120 minutes at 4 °C** for the wash.
   - **Size-exclusion chromatography (SEC):** concentrate the clarified medium
     if required by the validated column workflow; load the sample, collect
     and identify EV-containing fractions, pool those fractions, and
     concentrate if needed.
5. Gently resuspend the final pellet or adjust the pooled SEC preparation to a
   **recorded final volume**. Use the sample label **2. External exosomes
   (EXT)** and describe it as a **Mary-X conditioned-medium EV-enriched
   preparation**. Proceed to characterization; store the designated aliquots
   separately at **−80 °C** as described below.

The **2,000 × g, 15-minute, 4 °C** step replaces the previous 10–20-minute
range. It does not replace the source's **100 × g** spheroid-handling steps
or the later enrichment steps. Record the rotor, tube type, fill volume,
RCF convention (average or maximum), run time, and temperature. The
ultracentrifugation range remains a starting framework requiring rotor-specific
validation; follow the rotor and tube manufacturer's operating requirements.
""".strip(),
    ),
    (
        "Intracellular vesicles — Separate trypsin dissociation workflow",
        """
This section retains the earlier intracellular preparation as a separate
workflow. It is not part of the supplied culture-file procedure. Use an
allocated spheroid sample and process it independently of conditioned-medium EVs.

1. Collect the spheroid aliquot and wash gently with cold PBS **3 times**,
   using the laboratory's validated spheroid-recovery conditions. Keep any
   wash fractions separately if they are needed for interpretation.
2. Remove PBS and add enough **trypsin-EDTA** to cover the spheroid pellet,
   using the laboratory's established concentration. Following the
   researcher-specified procedure, **incubate at 37 °C and vortex every
   30 minutes**. During trypsin incubation, **gently pipette the suspension
   up and down multiple times using a 1 mL filtered pipette tip** to help
   dissociate the spheroids. After mixing, **check under the microscope
   for complete spheroid dissociation**. Stop incubation when complete
   dissociation is confirmed. Record the trypsin concentration, total
   incubation time, vortex speed and duration, number of pipetting strokes,
   and microscopic observations.
   The vortex speed, duration per mixing event, and maximum total trypsin
   exposure time have not been supplied; use the laboratory's established
   settings and exposure limit.
3. Once microscopy confirms complete dissociation, promptly neutralize
   trypsin with **DMEM + 10% exosome-depleted FBS + Antibiotic-Antimycotic
   (Anti-Anti)**. Record the neutralization medium volume, supplement lots,
   and Anti-Anti final concentration used.
4. Collect the dissociated cells at approximately **300–500 × g for
   5 minutes at 4 °C**. Remove supernatant and wash cells with cold PBS
   **2–3 times** to reduce residual trypsin and extracellular material.
5. After neutralization and washing, **count cells using an automated cell
   counter with trypan blue** before homogenization. Follow the counter's
   trypan blue staining instructions and record the counter model and stain
   mixing ratio. Record **total and viable cell concentrations, suspension
   volume, total and viable cell numbers, and percentage viability**.
   Normalize starting material across samples using the recorded counts.
6. Resuspend in ice-cold isotonic homogenization buffer compatible with the
   downstream assay, with appropriate inhibitors. The earlier buffer example
   was **250 mM sucrose, 20 mM HEPES, approximately pH 7.4**. Apply a validated
   controlled mechanical disruption method, such as Dounce homogenization,
   while keeping the preparation cold.
7. Process the homogenate using the earlier differential-centrifugation
   framework: **500–1,000 × g for 10 minutes at 4 °C**, transfer supernatant;
   **10,000 × g for 20–30 minutes at 4 °C**, transfer supernatant;
   approximately **100,000 × g for 70–120 minutes at 4 °C**, retain pellet.
   Gently wash/resuspend in a compatible buffer and repeat the high-speed
   centrifugation under the validated conditions.
8. Record the final resuspension volume and use the sample label **1. Internal
   exosome (INT)**. Describe the result as a **Mary-X intracellular
   membrane/vesicle-enriched preparation** and store the designated aliquots
   separately at **−80 °C**. Differential
   centrifugation alone does not establish endosomal origin or distinguish
   native intracellular vesicles from other membranes generated during
   cell disruption; use compartment-specific validation for that claim.

Trypsin is used for dissociation, not as an intracellular EV isolation reagent.
Record exposure consistently because proteolysis can affect protein readouts.
Do not apply trypsin to the conditioned-medium EV preparation in this workflow.
""".strip(),
    ),
    (
        "Controls, characterization, normalization, and storage",
        """
- Process a **cell-free medium control containing DMEM, 10% exosome-depleted
  FBS, and Anti-Anti** through the same **5-day incubation** and isolation
  workflow. Match supplement lots and the Anti-Anti final concentration.
  Include whole-cell lysate, viability
  records, and matched processing/storage controls. Retain the post-enrichment
  supernatant as a soluble-fraction control when appropriate; residual EVs
  may remain in it.
- Characterize particles with NTA or an equivalent validated method, imaging
  such as TEM/cryo-EM, and a panel of EV-associated and contamination markers.
  Examples carried forward from the earlier SOP include **CD9, CD63, CD81,
  TSG101, and ALIX**. Interpret marker selection and results for each fraction;
  intracellular organelle markers have a different meaning in cell-derived
  fractions than in conditioned-medium preparations.
- NTA measures particles and does not by itself establish EV identity. Use
  **EV-enriched preparation** unless stronger subtype/biogenesis evidence is
  available. Apply MISEV2023 characterization/reporting guidance; it does not
  validate these specific Mary-X culture or centrifugation settings.
- Report conditioned-medium volume, final preparation volume, collection
  interval, viable-cell input or justified spheroid-biomass estimate, and
  particles/protein using a consistent normalization strategy. Use comparable
  spheroid ages, sizes, and treatment conditions.
- Proceed promptly to characterization when possible. Keep preparations cold
  during short-term processing. Aliquot the final **1. Internal exosome (INT)**
  and **2. External exosomes (EXT)** samples into separate labeled low-binding
  tubes and **store both samples at −80 °C**. Record the aliquot volume,
  date frozen, freezer/rack/box/position, and freeze-thaw history. Keep INT and
  EXT samples separate and avoid unnecessary repeated freeze-thaw cycles.

Before comparing groups, review viability, medium-control background, multiple
characterization readouts, contamination, normalized starting material, and
matched processing/storage. Define study-specific acceptance criteria before
collection rather than inventing universal cutoffs.

Reference for EV nomenclature and characterization:
[Welsh et al., MISEV2023, Journal of Extracellular Vesicles (2024)](https://doi.org/10.1002/jev2.12404).
""".strip(),
    ),
    (
        "Experiment record",
        """
Record the following in the notebook entry and its Notes field:

- Researcher; date; Mary-X identifier/passage; treatment; replicate/set;
  spheroid number or density, size, morphology, and viability.
- DMEM formulation and lot; exosome-depleted FBS product, lot, and **10%**
  final proportion; Anti-Anti product, stock strength, added volume, and final
  concentration; PBS wash count and volume; **5-day incubation** start/end;
  actual medium collection interval; any feeding or medium changes;
  recovered conditioned-medium volume.
- Each centrifugation's sample fraction, RCF, RCF convention, duration,
  temperature, rotor, tube type/fill, and brake setting where specified.
- Trypsin concentration and total incubation time at **37 °C**; **30-minute
  vortexing intervals**, vortex speed and duration, repeated up-and-down
  pipetting with a **1 mL filtered pipette tip**, number of pipetting strokes,
  microscopic observations, and the time complete dissociation was confirmed;
  neutralization with **DMEM +
  10% exosome-depleted FBS + Antibiotic-Antimycotic (Anti-Anti)**, including
  medium volume, supplement lots, and Anti-Anti final concentration;
  cell wash details for the intracellular arm only.
- **Automated cell count with trypan blue**: counter model, stain mixing
  ratio, total/viable cell concentrations, suspension volume, total/viable
  cell numbers, percentage viability, and normalization method; EV separation
  method; SEC column/fraction details if used; final preparation volume.
- Sample fraction and tube label (**1. Internal exosome / INT** or
  **2. External exosomes / EXT**); particle size/concentration, NTA settings
  and dilution; protein/marker results; aliquot volume; date frozen;
  **−80 °C** storage location (freezer/rack/box/position); freeze-thaw history;
  deviations and QC disposition.

The existing app calculates total measured particles as concentration × unit
multiplier × dilution factor × final volume in mL, then normalizes by the
entered cell counts. A **50 µL** final volume is **0.050 mL**. Apply the NTA
dilution factor only once; use a factor of 1 if the entered concentration
has already been corrected for dilution.
""".strip(),
    ),
]

MARYX_SOP_TEXT = (
    "# Mary-X spheroid culture and EV collection SOP\n\n"
    f"Version {MARYX_SOP_VERSION} | Updated {MARYX_SOP_UPDATED}\n"
    f"Culture source: {MARYX_SOP_SOURCE}\n\n"
    + MARYX_SOP_NOTES
    + "\n\n"
    + MARYX_SAMPLE_SUMMARY
    + "\n\n"
    + "\n\n".join(f"## {title}\n\n{body}" for title, body in MARYX_SOP_SECTIONS)
    + "\n"
)

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
    ["➕ Add Entry", "📓 Notebook (view / edit)", "⚙️ Manage Presets", "🧪 Mary-X Exosome SOP"]
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
            "1. Internal exosome — tube label",
            value=f"{suggested_base}_INT",
            help="INT identifies the intracellular membrane/vesicle-enriched sample in this SOP. Store separately at −80 °C.",
        )
    with rcol:
        tube_label_external = st.text_input(
            "2. External exosomes — tube label",
            value=f"{suggested_base}_EXT",
            help="EXT identifies the conditioned-medium EV-enriched sample. Store separately at −80 °C.",
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

            st.bar_chart(
                chart_df,
                x="entry_label",
                y=metric_col,
                color=color_col,
            )

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
# TAB 4 — Mary-X culture and EV collection SOP
# ------------------------------------------------------------------
with tab_sop:
    st.subheader("Mary-X spheroid culture and EV collection SOP")
    st.caption(
        f"Version {MARYX_SOP_VERSION} · Updated {MARYX_SOP_UPDATED} · "
        f"Culture source: {MARYX_SOP_SOURCE}"
    )
    st.image(MARYX_SAMPLE_DIAGRAM_SVG, width=860)
    st.caption(
        "Sample names follow your labels. Internal = intracellular membrane/vesicle-enriched "
        "preparation; external = conditioned-medium EV-enriched preparation. "
        "Store both as separate labeled aliquots at −80 °C."
    )
    st.markdown(MARYX_SOP_NOTES)
    st.download_button(
        "⬇️ Download SOP as TXT",
        data=MARYX_SOP_TEXT.encode("utf-8"),
        file_name=f"MaryX_culture_and_EV_collection_SOP_v{MARYX_SOP_VERSION.replace('.', '_')}.txt",
        mime="text/plain",
        key="download_maryx_sop",
    )
    st.download_button(
        "⬇️ Download sample diagram as SVG",
        data=MARYX_SAMPLE_DIAGRAM_SVG.encode("utf-8"),
        file_name="MaryX_two_sample_workflow.svg",
        mime="image/svg+xml",
        key="download_maryx_sample_diagram",
    )
    for section_number, (section_title, section_body) in enumerate(MARYX_SOP_SECTIONS):
        with st.expander(section_title, expanded=section_number < 3):
            st.markdown(section_body)

