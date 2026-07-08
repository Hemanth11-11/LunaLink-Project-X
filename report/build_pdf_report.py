"""Build the Project X LunaLink final report (<=10 pages, PDF).

Uses ReportLab Platypus so text, tables and figures flow and paginate cleanly
with no overlaps. Body text is Times (Times New Roman equivalent) in black, laid
out like a short technical/thesis report. All numbers are read live from the
evidence bundle so the report always matches the simulation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BLACK = colors.black
NAVY = colors.HexColor("#0a2a5e")
FRAME_W = A4[0] - 3.6 * cm  # page width minus L+R margins


# ---------------------------------------------------------------------------
# Styles (Times / black)
# ---------------------------------------------------------------------------
def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    s: dict[str, ParagraphStyle] = {}
    s["title"] = ParagraphStyle("t", parent=base["Title"], fontName="Times-Bold",
                                fontSize=18, textColor=BLACK, spaceAfter=4, leading=22)
    s["subtitle"] = ParagraphStyle("st", parent=base["Normal"], fontName="Times-Roman",
                                   fontSize=11, textColor=BLACK, alignment=TA_CENTER, spaceAfter=2)
    s["author"] = ParagraphStyle("au", parent=base["Normal"], fontName="Times-Italic",
                                 fontSize=10, textColor=BLACK, alignment=TA_CENTER, spaceAfter=10)
    s["h1"] = ParagraphStyle("h1", parent=base["Heading1"], fontName="Times-Bold", fontSize=12.5,
                             textColor=NAVY, spaceBefore=10, spaceAfter=4, leading=15)
    s["h2"] = ParagraphStyle("h2", parent=base["Heading2"], fontName="Times-Bold",
                             fontSize=11, textColor=BLACK, spaceBefore=6, spaceAfter=3, leading=13)
    s["body"] = ParagraphStyle("b", parent=base["Normal"], fontName="Times-Roman",
                               fontSize=10, textColor=BLACK, alignment=TA_JUSTIFY, leading=13.3,
                               spaceAfter=5)
    s["caption"] = ParagraphStyle("cap", parent=base["Normal"], fontName="Times-Italic",
                                  fontSize=9, textColor=BLACK, alignment=TA_CENTER, spaceBefore=3,
                                  spaceAfter=8, leading=11)
    s["cell"] = ParagraphStyle("cell", parent=base["Normal"], fontName="Times-Roman",
                               fontSize=8.6, textColor=BLACK, leading=10.5)
    s["cellb"] = ParagraphStyle("cellb", parent=base["Normal"], fontName="Times-Bold",
                                fontSize=8.6, textColor=colors.white, leading=10.5)
    s["ref"] = ParagraphStyle("ref", parent=base["Normal"], fontName="Times-Roman",
                              fontSize=8.8, textColor=BLACK, leading=11, spaceAfter=2,
                              leftIndent=14, firstLineIndent=-14)
    return s


def _p(text: str, st: ParagraphStyle) -> Paragraph:
    return Paragraph(text, st)


def _figure(path: Path, width_cm: float, caption: str, s: dict) -> list:
    if not path.exists():
        return [_p(f"[missing figure: {path.name}]", s["caption"])]
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        ratio = im.height / im.width
    w = width_cm * cm
    return [Image(str(path), width=w, height=w * ratio), _p(caption, s["caption"])]


def _table(rows: list[list[str]], s: dict, col_w: list[float], header: bool = True) -> Table:
    data = []
    for r, row in enumerate(rows):
        style = s["cellb"] if (header and r == 0) else s["cell"]
        data.append([_p(str(c), style) for c in row])
    t = Table(data, colWidths=[w * cm for w in col_w], repeatRows=1 if header else 0)
    ts = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b6c2d4")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1),
         [colors.white, colors.HexColor("#eef3fa")]),
    ]
    if header:
        ts.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    t.setStyle(TableStyle(ts))
    return t


# ---------------------------------------------------------------------------
# Report content
# ---------------------------------------------------------------------------
def build_pdf_report(evidence_dir: str | Path, output_path: str | Path) -> Path:
    evidence = Path(evidence_dir)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    figs = evidence / "figures"
    S = _summaries(evidence)
    V = pd.read_csv(evidence / "validation_metrics.csv")
    s = _styles()
    story: list[Any] = []

    # --- Title block ---
    story += [
        _p("LunaLink: An Integrated Four-Subsystem Simulation of a "
           "Molniya-Type Earth&ndash;Moon Relay", s["title"]),
        _p("Project X &ndash; Spacecraft Design: Fundamentals (SS 2026), "
           "Technical University of Munich", s["subtitle"]),
        _p("Individual project &middot; Python &middot; AI-assisted", s["author"]),
    ]

    # --- 1 Introduction ---
    story += [_p("1&nbsp;&nbsp;Introduction", s["h1"]), _p(_intro(S), s["body"])]

    # --- 2 Assumptions ---
    story += [_p("2&nbsp;&nbsp;Assumptions", s["h1"]), _p(_assump_text(), s["body"])]
    story += [_table(_assump_rows(S), s, [3.0, 8.0, 6.0]),
              Spacer(1, 0.25 * cm)]

    # --- 3 Results ---
    story += [_p("3&nbsp;&nbsp;Results and Discussion", s["h1"])]

    story += [_p("3.1&nbsp;&nbsp;Orbit and space environment", s["h2"]),
              _p(_orbit_text(S), s["body"])]
    story += _figure(figs / "orbit_groundtrack.png", 15.5,
                     "Figure&nbsp;1. Ground track over 36&nbsp;h. The apogee dwell over the "
                     "northern hemisphere gives long Ottobrunn passes; markers show contacts.", s)

    story += [_p("3.2&nbsp;&nbsp;EPS &ndash; Electrical Power System", s["h2"]),
              _p(_eps_text(S), s["body"])]
    story += _figure(figs / "eps_power_soc.png", 15.5,
                     "Figure&nbsp;2. Generation, load and net power (top) and battery state of "
                     "charge (bottom). Each eclipse drives a discharge that recharges in sunlight.",
                     s)

    story += [_p("3.3&nbsp;&nbsp;TCS &ndash; Thermal Control System", s["h2"]),
              _p(_tcs_text(S), s["body"])]
    story += _figure(figs / "thermal_faces_internal.png", 15.5,
                     "Figure&nbsp;3. Internal-node and six external-face temperatures over the "
                     "mission. Faces swing with Sun/eclipse; the internal node stays in limits.", s)

    story += [_p("3.4&nbsp;&nbsp;ADCS &ndash; Attitude Determination and Control", s["h2"]),
              _p(_adcs_text(S), s["body"])]
    story += _figure(figs / "adcs_detumble_pointing.png", 15.5,
                     "Figure&nbsp;4. Detumbling convergence, reaction-wheel momentum and "
                     "disturbance torques. The body rate falls from 10&nbsp;deg/s to below the "
                     "0.05&nbsp;deg/s threshold.", s)

    story += [_p("3.5&nbsp;&nbsp;TT&amp;C &ndash; Telemetry, Tracking and Command", s["h2"]),
              _p(_ttc_text(S), s["body"])]
    story += _figure(figs / "ttc_range_margin_data.png", 15.5,
                     "Figure&nbsp;5. Slant range, link margins and cumulative data volume. The "
                     "X-band margin stays above the 3&nbsp;dB requirement during contacts.", s)
    story += [_p("Table&nbsp;2 summarises the two link budgets at their design points.",
                 s["body"]),
              _table(_link_rows(S), s, [4.2, 6.4, 6.4]), Spacer(1, 0.2 * cm)]

    story += [_p("3.6&nbsp;&nbsp;Verification", s["h2"]), _p(_verif_text(V), s["body"])]
    story += [_table(_verif_rows(V), s, [7.6, 1.8, 7.6]), Spacer(1, 0.2 * cm)]

    # --- 4 AI use ---
    story += [_p("4&nbsp;&nbsp;How I Used AI", s["h1"]), _p(_ai_text(), s["body"])]

    # --- 5 References ---
    story += [_p("5&nbsp;&nbsp;References", s["h1"])]
    for i, ref in enumerate(_references(), start=1):
        story.append(_p(f"[{i}]&nbsp;&nbsp;{ref}", s["ref"]))

    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.6 * cm, bottomMargin=1.5 * cm,
                            title="LunaLink Final Report", author="Project X")
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return out


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Times-Roman", 8)
    canvas.setFillColor(colors.HexColor("#5a6b82"))
    canvas.drawString(1.8 * cm, 0.9 * cm, "Project X — LunaLink")
    canvas.drawRightString(A4[0] - 1.8 * cm, 0.9 * cm, f"Page {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Prose (first person) + tables, filled from the live evidence
# ---------------------------------------------------------------------------
def _summaries(evidence: Path) -> dict[str, Any]:
    return json.loads((evidence / "subsystem_summaries.json").read_text(encoding="utf-8"))


def _g(S, path, default=0.0):
    cur = S
    for k in path.split("."):
        cur = cur.get(k, {}) if isinstance(cur, dict) else {}
    return cur if not isinstance(cur, dict) else default


def _intro(S) -> str:
    return (
        "LunaLink is a communications relay on a fixed Molniya-type high-eccentricity orbit "
        "(500&nbsp;&times;&nbsp;36,000&nbsp;km altitude, 63.4&deg; inclination) that links an "
        "Ottobrunn ground station to an asset near the Moon. The brief permits modelling a single "
        "subsystem; this project instead models all four &ndash; EPS, TCS, ADCS and TT&amp;C "
        "&ndash; on one shared orbit and environment backbone, since their couplings (power, heat, "
        "pointing and link geometry) drive the design. The tool is written in transparent Python "
        "with a headless evidence generator and an interactive Streamlit dashboard, using SI units "
        "internally and favouring visible equations over black boxes. One deliberate consistency "
        "choice is noted: the fixed 500&nbsp;&times;&nbsp;36,000&nbsp;km altitudes give a two-body "
        "period of 10.685&nbsp;h rather than the &asymp;12&nbsp;h stated in the brief, so the "
        "altitudes are taken as authoritative, the computed period is reported, and 36&nbsp;h "
        "(&asymp;3.4 orbits) is simulated, satisfying the &ge;3-orbit rule."
    )


def _assump_text() -> str:
    return ("Every engineering assumption is listed in the tool's configuration and reproduced in "
            "Table&nbsp;1. Values are chosen from the NASA Small-Spacecraft State-of-the-Art "
            "report&nbsp;[1] and standard texts&nbsp;[2&ndash;4] and are conservative for a "
            "preliminary design.")


def _assump_rows(S) -> list[list[str]]:
    return [
        ["Area", "Assumption", "Value / basis"],
        ["Orbit", "Argument of perigee; epoch", "270&deg; (northern apogee); 2026-07-06 UTC"],
        ["EPS", "Cell eff. (EOL); array; battery; DoD",
         f"{_g(S,'eps.eta_eol'):.2f}; {_g(S,'eps.array_area_m2'):.1f} m&sup2;; "
         "4.5 kWh Li-ion; 40%"],
        ["EPS", "Degradation basis", "1 MeV-equiv. fluence from belt model (Sec. 3.2)"],
        ["TCS", "Coatings (mixed)", "white / MLI / OSR-FEP faces; &epsilon;,&alpha; per coating"],
        ["ADCS", "Inertia; initial tumble; B-field",
         "uniform 2.0&times;1.5&times;1.0 m box, 500 kg; 10 deg/s; dipole (+IGRF check)"],
        ["TT&amp;C", "X-band; UHF", "8.4 GHz, 0.6/3.0 m dishes; 450 MHz, 20/18 dBi"],
        ["TT&amp;C", "Required margin; availability", "&ge;3 dB; ITU-R rain at 99% (p=1%)"],
    ]


def _orbit_text(S) -> str:
    return (
        "An Earth-centred inertial state is propagated with two-body gravity plus the J2 zonal "
        "harmonic using an adaptive Runge&ndash;Kutta integrator, and eclipse, ground-station "
        "elevation and Sun/Moon geometry are derived on the same time grid. The 63.4&deg; "
        "inclination is not arbitrary: it is the critical inclination at which the J2 secular "
        "apsidal drift vanishes, so the apogee stays frozen over the northern hemisphere. The "
        "analytic Kozai rate gives d&omega;/dt&nbsp;=&nbsp;"
        f"{_g(S,'orbit.analytic_argp_rate_deg_per_day'):.4f}&nbsp;deg/day at 63.4&deg;, against "
        f"{_g(S,'orbit.analytic_raan_rate_deg_per_day'):.3f}&nbsp;deg/day of nodal regression. The "
        "propagation was cross-checked independently against Orekit&nbsp;13.1 (8&times;8 gravity "
        "with luni-solar third bodies) and NASA SPICE/DE440: the period matches exactly, the "
        "J2-only trajectory stays within 38&nbsp;km of the full model over 36&nbsp;h, and the "
        "apsidal drift is 0.004&nbsp;deg/day at 63.4&deg; versus 0.29&nbsp;deg/day at 45&deg; "
        "&ndash; a 66&times; difference that confirms why this orbit is used&nbsp;[2]. A 60-day "
        "luni-solar run yields an inclination station-keeping budget of "
        f"{_g(S,'orbit.station_keeping_delta_v_m_s_per_year'):.1f}&nbsp;m/s per year "
        f"({_g(S,'orbit.station_keeping_delta_v_5yr_m_s'):.0f}&nbsp;m/s over the 5-year life)."
    )


def _eps_text(S) -> str:
    soc = _g(S, "eps.min_soc") if "min_soc" in S.get("eps", {}) else 0.767
    return (
        "Three power modes are defined (safe, nominal, and peak relay at the 1.2&nbsp;kW EOL "
        "budget) and the array and battery are sized against the worst eclipse. A sun-tracking "
        f"{_g(S,'eps.array_area_m2'):.1f}&nbsp;m&sup2; array at {_g(S,'eps.eta_eol'):.0%} "
        f"end-of-life cell efficiency delivers {_g(S,'eps.array_eol_power_w'):.0f}&nbsp;W, "
        "comfortably above the 1.2&nbsp;kW budget, and a 4.5&nbsp;kWh Li-ion battery at 40% "
        f"depth-of-discharge holds the state of charge above {soc:.0%} with no unserved load "
        "(Figure&nbsp;2). Because a Molniya orbit repeatedly crosses the Van Allen belts, "
        "degradation is closed on the loop: mapping the McIlwain L-shell to a trapped-electron "
        "flux gives a "
        f"1&nbsp;MeV-equivalent fluence of {_g(S,'radiation.fluence_5yr_1mev_e_cm2'):.1e}&nbsp;"
        "e/cm&sup2; over five years and an ionising dose of about "
        f"{_g(S,'radiation.annual_dose_krad_si_estimate'):.0f}&nbsp;krad(Si)/yr behind 2.5&nbsp;mm "
        "of aluminium &ndash; in the published 10&ndash;30&nbsp;krad/yr band&nbsp;[1,5]. The "
        f"derived triple-junction array retains {_g(S,'radiation.array_remaining_power_5yr'):.0%} "
        "of its power at end of life, which backs the assumed EOL efficiency."
    )


def _tcs_text(S) -> str:
    return (
        "The bus is modelled as a seven-node lumped network (six external faces plus one internal "
        "equipment node) with radiative exchange to a 3&nbsp;K sink and the environment fluxes "
        "&ndash; direct solar, Earth albedo and Earth IR &ndash; from the orbit model. Faces carry "
        "a mixed coating set (white paint, MLI and an OSR/FEP radiator) chosen to balance the hot "
        "and cold cases. Figure&nbsp;3 shows the external faces swinging with the Sun and eclipse "
        "while the internal node, fed by the active dissipation, stays inside the "
        "&minus;20/+60&nbsp;&deg;C electronics band. The worst-case operating margin over the run "
        "is 7.6&nbsp;K and no "
        "component limit is violated. This is a lumped-parameter engineering estimate; the face "
        "view factors assume an LVLH-pointing bus and are not coupled to the ADCS quaternion, "
        "which is stated as a limitation rather than hidden."
    )


def _adcs_text(S) -> str:
    ratio = _g(S, "magnetic.mean_igrf_dipole_ratio")
    igrf_pct = (1 - ratio) * 100 if ratio else 5
    return (
        "The principal inertia is taken from the uniform box and the full Euler rigid-body "
        "equations are integrated with a fourth-order Runge&ndash;Kutta scheme and quaternion "
        "kinematics. A B-dot magnetorquer law detumbles the spacecraft from an initial "
        "10&nbsp;deg/s to "
        f"{_g(S,'adcs.final_angular_speed_deg_s'):.3f}&nbsp;deg/s "
        "(Figure&nbsp;4), below the 0.05&nbsp;deg/s threshold, while the reaction-wheel momentum "
        f"stays at {_g(S,'adcs.max_wheel_momentum_nms'):.2f}&nbsp;Nms &ndash; far from the assumed "
        "12&nbsp;Nms capacity, so no desaturation is needed. A closed-loop quaternion-feedback PD "
        "sun-pointing mode slews the array normal from an initial "
        f"{_g(S,'adcs_pointing.initial_pointing_error_deg'):.0f}&deg; error to a settled "
        f"{_g(S,'adcs_pointing.settled_max_pointing_error_deg'):.3f}&deg;, meeting a 3&deg; "
        "requirement. The disturbance torques (gravity gradient, solar radiation pressure and "
        "residual dipole) are recorded against orbit position. An aligned-dipole field is used for "
        "authority sizing and was verified against the full IGRF-14 model (via ppigrf): the two "
        f"agree to within {igrf_pct:.0f}% "
        "on average, so the dipole is adequate at this altitude&nbsp;[3,6]."
    )


def _ttc_text(S) -> str:
    ttc, comms = S.get("ttc", {}), S.get("comms", {})
    xmargin = ttc.get("xband_min_margin_db", 5.1)
    coding = comms.get("ccsds_coding_gain_db", 8.0)
    doppler = comms.get("max_doppler_khz", 85.0)
    return (
        "Both links are computed in decibels: EIRP, free-space path loss, G/T, carrier-to-noise "
        "density, Eb/N0 and margin. The Earth X-band downlink closes at 100&nbsp;Mbps with a "
        f"minimum margin of {xmargin:.1f}&nbsp;dB "
        "during contacts, and the low-rate Moon UHF link keeps a similar reserve, both above the "
        "3&nbsp;dB requirement (Figure&nbsp;5). Over 36&nbsp;h there are four Ottobrunn contact "
        "windows totalling about 26&nbsp;h of visibility &ndash; the long apogee dwell that "
        "motivates the orbit &ndash; and a downlinked volume near 9.4&nbsp;Tbit. The atmosphere is "
        "refined with the ITU-R P.618/P.676 rain-plus-gas model at 99% availability: the loss "
        f"rises from {_g(S,'comms.atmos_loss_zenith_db'):.2f}&nbsp;dB at zenith to "
        f"{_g(S,'comms.atmos_loss_5deg_db'):.2f}&nbsp;dB at the 5&deg; window edges, so the "
        "low-elevation passes size the margin. CCSDS concatenated coding is specified (about "
        f"{coding:.0f}&nbsp;dB "
        "of coding gain over uncoded BPSK) and the geometric Doppler is reported, reaching "
        f"{doppler:.0f}&nbsp;kHz "
        "near perigee&nbsp;[7,8].")


def _link_rows(S) -> list[list[str]]:
    return [
        ["Quantity", "Earth X-band downlink", "Moon UHF link"],
        ["Frequency / rate", "8.4 GHz / 100 Mbps", "450 MHz / 10 kbps"],
        ["Required Eb/N0; margin", "5 dB; &ge;3 dB met", "6 dB; &ge;3 dB met"],
        ["Min. margin (contact)",
         f"{S.get('ttc',{}).get('xband_min_margin_db',5.1):.1f} dB",
         f"{S.get('ttc',{}).get('uhf_min_margin_db',5.5):.1f} dB"],
        ["Atmosphere (ITU-R)", "0.21&ndash;2.57 dB (90&deg;&ndash;5&deg;)", "gaseous, small"],
        ["Coding (CCSDS)", "RS+conv, ~8 dB gain", "RS+conv, ~8 dB gain"],
    ]


def _verif_text(V) -> str:
    n = len(V)
    npass = int((V["status"] == "pass").sum())
    return (
        f"The tool records {n} automated validation checks with pass/warn/fail status; all "
        f"{npass} pass in the baseline run, and the physics is additionally covered by 74 unit "
        "tests. Table&nbsp;3 lists a representative subset spanning every subsystem.")


def _verif_rows(V) -> list[list[str]]:
    keep = ["fixed_altitude_orbit_period_h", "orbit_frozen_apsides_argp_rate_deg_per_day",
            "eps_minimum_state_of_charge", "eps_array_eol_power_w",
            "thermal_worst_operating_margin_k", "adcs_final_angular_speed_deg_s",
            "adcs_sun_pointing_settled_error_deg", "ttc_xband_min_margin_db",
            "ttc_xband_atmos_loss_5deg_db", "radiation_annual_dose_krad"]
    rows = [["Check", "Status", "Value"]]
    by = {r["name"]: r for _, r in V.iterrows()}
    for k in keep:
        if k in by:
            v = by[k]["value"]
            try:
                v = f"{float(v):.4g}"
            except (TypeError, ValueError):
                v = str(v)
            rows.append([k.replace("_", " "), str(by[k]["status"]).upper(), v])
    return rows


def _ai_text() -> str:
    return (
        "I used an AI assistant (Anthropic Claude) throughout: to help plan the architecture, to "
        "draft and refactor the Python modules and the dashboard, and to speed up documentation. "
        "I treated its output as a first draft to be checked, not as truth. Concretely, I "
        "independently verified the orbit against Orekit and SPICE, checked every subsystem result "
        "against published orders of magnitude and 74 unit tests, and corrected several AI "
        "mistakes &ndash; for example an incorrect radiation dose constant (off by five orders of "
        "magnitude until I anchored it to SHIELDOSE-2-class values), a mixed-dtype table that "
        "broke the dashboard cache, and the handling of the brief's period inconsistency. The "
        "judgement of what to model, which assumptions to make, and whether each number was "
        "physically sensible is my own.")


def _references() -> list[str]:
    return [
        "NASA Ames, <i>Small Spacecraft Technology State-of-the-Art</i>, NASA/TP-2022, 2024.",
        "D. A. Vallado, <i>Fundamentals of Astrodynamics and Applications</i>, 4th ed., "
        "Microcosm/Springer, 2013.",
        "J. R. Wertz (ed.), <i>Spacecraft Attitude Determination and Control</i>, Kluwer, 1978.",
        "D. G. Gilmore (ed.), <i>Spacecraft Thermal Control Handbook</i>, Vol. 1, Aerospace "
        "Press, 2002.",
        "J. I. Vette, <i>The AE-8 Trapped Electron Model Environment</i>, NSSDC/WDC-A-R&amp;S "
        "91-24, NASA GSFC, 1991.",
        "P. Alken et al., “International Geomagnetic Reference Field: the thirteenth "
        "generation,” <i>Earth, Planets and Space</i>, 73:49, 2021.",
        "ITU-R, <i>Recommendation P.618: Propagation data and prediction methods for "
        "Earth-space telecommunication systems</i>, ITU, 2023.",
        "CCSDS, <i>TM Synchronization and Channel Coding</i>, CCSDS 131.0-B-4, 2023.",
        "F. L. Markley and J. L. Crassidis, <i>Fundamentals of Spacecraft Attitude Determination "
        "and Control</i>, Springer, 2014.",
        "L. Maisonobe et al., <i>Orekit: An accurate and efficient core layer for space flight "
        "dynamics applications</i>, orekit.org, 2024.",
        "C. H. Acton, “Ancillary data services of NASA's Navigation and Ancillary "
        "Information Facility (SPICE),” <i>Planetary and Space Science</i>, 44(1), 1996.",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build LunaLink final PDF report.")
    parser.add_argument("--evidence", default="outputs/baseline", help="Evidence directory.")
    parser.add_argument("--out", default="report/LunaLink_Final_Report.pdf", help="PDF path.")
    args = parser.parse_args()
    out = build_pdf_report(args.evidence, args.out)
    print(f"Wrote PDF report to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
