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

MARYX_SOP_VERSION = "1.8"
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

**Trypsin percentage:** **___% — to be confirmed.** The trypsin concentration
has not been supplied. Enter the laboratory's actual trypsin-EDTA percentage
before using the dissociation instructions.

**Sucrose isolation:** The diagram applies **100,000 × g with 30% sucrose in
PBS** to the two preparations processed separately. The sucrose concentration
basis, cushion/gradient arrangement, run duration, EV recovery fraction, and
subsequent wash/buffer-exchange procedure require confirmation. The **4 °C**
temperature is carried forward from the existing SOP.

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
MARYX_SAMPLE_DIAGRAM_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1360" viewBox="0 0 1000 1360" role="img" aria-labelledby="maryx-title maryx-description">
<title id="maryx-title">Mary-X detailed two-sample workflow and storage</title>
<desc id="maryx-description">The internal branch shows trypsin dissociation at 37 degrees Celsius with the percentage awaiting confirmation, vortexing every 30 minutes, repeated pipetting, microscopy, neutralization, washing, and automated cell counting. The external branch shows 300 times g, then 2000 times g for 15 minutes at 4 degrees Celsius, then 10000 times g for approximately 30 minutes at 4 degrees Celsius, retaining the supernatant after each clarification step. Both separate preparations show isolation at 100000 times g with 30 percent sucrose in PBS; run time, sucrose setup, and fraction recovery require confirmation. Store both samples separately at minus 80 degrees Celsius.</desc>
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L10,5 L0,10 Z" fill="#53627a"/></marker></defs>
<rect width="1000" height="1360" fill="#ffffff"/>
<g font-family="Arial, DejaVu Sans, sans-serif" text-anchor="middle" fill="#172b44">
<text x="500" y="39" font-size="29" font-weight="700" fill="#172b44">Mary-X detailed two-sample workflow</text>
<text x="500" y="70" font-size="19" font-weight="400" fill="#526276">Keep the internal and external preparations separate throughout</text>
<rect x="170" y="95" width="660" height="104" rx="11" fill="#f2f5f9" stroke="#b8c3d1" stroke-width="1.5"/>
<text x="500" y="128" font-size="25" font-weight="700" fill="#172b44">Mary-X spheroids and conditioned medium</text>
<text x="500" y="157" font-size="19" font-weight="400" fill="#172b44">DMEM + 10% exosome-depleted FBS + Anti-Anti</text>
<text x="500" y="185" font-size="19" font-weight="400" fill="#172b44">5 days at 37 °C, 5% CO₂</text>
<path d="M500,199 V224 H250 V245" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<path d="M500,224 H750 V245" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<rect x="30" y="252" width="440" height="78" rx="11" fill="#f1f4ff" stroke="#637bb3" stroke-width="1.5"/>
<text x="250" y="284" font-size="25" font-weight="700" fill="#172b44">Retained spheroids</text>
<text x="250" y="313" font-size="19" font-weight="400" fill="#172b44">Reserved aliquot; gentle PBS washes ×3</text>
<rect x="530" y="252" width="440" height="78" rx="11" fill="#edf8f5" stroke="#318978" stroke-width="1.5"/>
<text x="750" y="284" font-size="25" font-weight="700" fill="#172b44">Conditioned medium</text>
<text x="750" y="313" font-size="19" font-weight="400" fill="#172b44">Supernatant from spheroid harvest</text>
<path d="M250,330 V351" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<path d="M750,330 V351" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<rect x="30" y="358" width="440" height="258" rx="11" fill="#ffffff" stroke="#637bb3" stroke-width="1.5"/>
<text x="250" y="392" font-size="25" font-weight="700" fill="#172b44">Trypsin dissociation</text>
<text x="250" y="429" font-size="23" font-weight="700" fill="#875600">Trypsin-EDTA: ___% (confirm)</text>
<text x="250" y="465" font-size="21" font-weight="700" fill="#172b44">37 °C · vortex every 30 minutes</text>
<text x="250" y="499" font-size="20" font-weight="400" fill="#172b44">Pipette up and down multiple times</text>
<text x="250" y="527" font-size="20" font-weight="400" fill="#172b44">with a 1 mL filtered pipette tip</text>
<text x="250" y="563" font-size="20" font-weight="400" fill="#172b44">Check under the microscope</text>
<text x="250" y="594" font-size="20" font-weight="700" fill="#172b44">Stop when dissociation is complete</text>
<path d="M250,616 V639" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<rect x="30" y="646" width="440" height="246" rx="11" fill="#ffffff" stroke="#637bb3" stroke-width="1.5"/>
<text x="250" y="681" font-size="24" font-weight="700" fill="#172b44">Neutralize, wash, and count</text>
<text x="250" y="714" font-size="20" font-weight="400" fill="#172b44">DMEM + 10% exosome-depleted FBS</text>
<text x="250" y="741" font-size="20" font-weight="400" fill="#172b44">+ Antibiotic-Antimycotic (Anti-Anti)</text>
<text x="250" y="776" font-size="21" font-weight="700" fill="#172b44">300–500 × g · 5 min · 4 °C</text>
<text x="250" y="805" font-size="19" font-weight="400" fill="#172b44">Retain cells; PBS wash 2–3×</text>
<text x="250" y="839" font-size="20" font-weight="400" fill="#172b44">Automated cell count with trypan blue</text>
<text x="250" y="870" font-size="18" font-weight="400" fill="#172b44">Record total cells, live cells, and viability (%)</text>
<path d="M250,892 V915" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<rect x="30" y="922" width="440" height="212" rx="11" fill="#ffffff" stroke="#637bb3" stroke-width="1.5"/>
<text x="250" y="957" font-size="23" font-weight="700" fill="#172b44">Intracellular preparation</text>
<text x="250" y="991" font-size="20" font-weight="400" fill="#172b44">Controlled cell homogenization</text>
<text x="250" y="1021" font-size="18" font-weight="400" fill="#172b44">Clarify using the intracellular workflow</text>
<text x="250" y="1052" font-size="20" font-weight="700" fill="#172b44">100,000 × g · 30% sucrose in PBS</text>
<text x="250" y="1083" font-size="18" font-weight="400" fill="#875600">Run time and fraction recovery: confirm</text>
<text x="250" y="1114" font-size="21" font-weight="700" fill="#172b44">Aliquot and label INT</text>
<rect x="530" y="358" width="440" height="94" rx="11" fill="#ffffff" stroke="#318978" stroke-width="1.5"/>
<text x="750" y="387" font-size="22" font-weight="700" fill="#172b44">Remove residual intact cells</text>
<text x="750" y="417" font-size="21" font-weight="700" fill="#172b44">300 × g · 10 min · 4 °C</text>
<text x="750" y="443" font-size="18" font-weight="400" fill="#172b44">Transfer supernatant</text>
<path d="M750,452 V475" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<rect x="530" y="482" width="440" height="128" rx="11" fill="#ffffff" stroke="#318978" stroke-width="1.5"/>
<text x="750" y="515" font-size="23" font-weight="700" fill="#172b44">Remove cells and debris</text>
<text x="750" y="552" font-size="25" font-weight="700" fill="#172b44">2,000 × g · 15 min · 4 °C</text>
<text x="750" y="587" font-size="19" font-weight="400" fill="#172b44">Transfer supernatant; leave pellet behind</text>
<path d="M750,610 V633" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<rect x="530" y="640" width="440" height="152" rx="11" fill="#ffffff" stroke="#318978" stroke-width="1.5"/>
<text x="750" y="674" font-size="22" font-weight="700" fill="#172b44">Remove larger debris</text>
<text x="750" y="714" font-size="25" font-weight="700" fill="#172b44">10,000 × g · ~30 min · 4 °C</text>
<text x="750" y="748" font-size="19" font-weight="400" fill="#172b44">Transfer supernatant; leave pellet behind</text>
<text x="750" y="777" font-size="18" font-weight="400" fill="#526276">Larger EVs may also be in this pellet</text>
<path d="M750,792 V815" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<rect x="530" y="822" width="440" height="312" rx="11" fill="#ffffff" stroke="#318978" stroke-width="1.5"/>
<text x="750" y="858" font-size="25" font-weight="700" fill="#172b44">EV isolation with sucrose</text>
<text x="750" y="897" font-size="25" font-weight="700" fill="#172b44">100,000 × g · 4 °C</text>
<text x="750" y="934" font-size="24" font-weight="700" fill="#172b44">30% sucrose in PBS</text>
<text x="750" y="972" font-size="19" font-weight="400" fill="#875600">Duration and sucrose setup: confirm</text>
<text x="750" y="1009" font-size="20" font-weight="400" fill="#172b44">Recover the EV-containing fraction</text>
<text x="750" y="1043" font-size="18" font-weight="400" fill="#875600">Confirm recovery and wash procedure</text>
<text x="750" y="1083" font-size="19" font-weight="400" fill="#172b44">Record final preparation volume</text>
<text x="750" y="1114" font-size="21" font-weight="700" fill="#172b44">Aliquot and label EXT</text>
<path d="M250,1134 V1157" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<path d="M750,1134 V1157" fill="none" stroke="#53627a" stroke-width="2.5" marker-end="url(#arrow)"/>
<rect x="30" y="1164" width="440" height="145" rx="11" fill="#eef2ff" stroke="#49669e" stroke-width="2"/>
<text x="250" y="1201" font-size="27" font-weight="700" fill="#172b44">1. Internal exosome</text>
<text x="250" y="1255" font-size="42" font-weight="700" fill="#172b44">−80 °C</text>
<text x="250" y="1289" font-size="20" font-weight="400" fill="#172b44">INT · separate labeled aliquots</text>
<rect x="530" y="1164" width="440" height="145" rx="11" fill="#e7f5ef" stroke="#257564" stroke-width="2"/>
<text x="750" y="1201" font-size="27" font-weight="700" fill="#172b44">2. External exosomes</text>
<text x="750" y="1255" font-size="42" font-weight="700" fill="#172b44">−80 °C</text>
<text x="750" y="1289" font-size="20" font-weight="400" fill="#172b44">EXT · separate labeled aliquots</text>
<text x="500" y="1343" font-size="19" font-weight="400" fill="#172b44">Label each tube with experiment ID, sample type, date, volume, and freezer location.</text>
</g></svg>"""

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
4. Isolate EVs using **100,000 × g with 30% sucrose in PBS** according to
   the researcher's update. **4 °C** is retained from the existing SOP.
   Confirm and record the run duration, rotor, tube/fill requirements, sucrose
   concentration basis and arrangement (for example, cushion or gradient),
   EV-containing fraction to recover, and subsequent wash/buffer-exchange
   procedure. These sucrose-method details have not yet been supplied; the
   earlier generic 70–120-minute direct-pelleting instructions do not establish
   the run time or recovery fraction for this revised step.
5. After the confirmed recovery and wash procedure, gently resuspend the
   final preparation to a **recorded final volume**. Use the sample label
   **2. External exosomes
   (EXT)** and describe it as a **Mary-X conditioned-medium EV-enriched
   preparation**. Proceed to characterization; store the designated aliquots
   separately at **−80 °C** as described below.

The **2,000 × g, 15-minute, 4 °C** step replaces the previous 10–20-minute
range. It does not replace the source's **100 × g** spheroid-handling steps
or the later enrichment steps. Record the rotor, tube type, fill volume,
RCF convention (average or maximum), run time, and temperature. The sucrose
ultracentrifugation settings require rotor-specific confirmation; follow the
rotor and tube manufacturer's operating requirements.
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
2. Remove PBS and add enough **trypsin-EDTA** to cover the spheroid pellet.
   Record the trypsin concentration as **___% (to be confirmed)** using the
   laboratory's actual reagent percentage. Following the
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
   **10,000 × g for 20–30 minutes at 4 °C**, transfer supernatant.
   For the final isolation, this revision applies the researcher's
   **100,000 × g with 30% sucrose in PBS** update, keeping the intracellular
   sample separate. **4 °C** is carried forward from the existing SOP.
   Confirm the sucrose setup, run time, EV-containing recovery fraction, and
   wash/buffer-exchange procedure before applying this revised isolation step.
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
- **100,000 × g sucrose isolation:** 30% sucrose in PBS; concentration basis;
  cushion/gradient or other arrangement; sucrose and sample volumes; run time;
  fraction recovered; and wash/buffer-exchange details for each sample.
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
    st.image(MARYX_SAMPLE_DIAGRAM_SVG, width=1000)
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

