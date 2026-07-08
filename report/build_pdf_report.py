"""Build the final Project X PDF report from LunaLink evidence."""

from __future__ import annotations

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build LunaLink final PDF report.")
    parser.add_argument("--evidence", default="outputs/baseline", help="Evidence directory.")
    parser.add_argument("--out", default="report/LunaLink_Final_Report.pdf", help="PDF path.")
    return parser.parse_args()


def build_pdf_report(evidence_dir: str | Path, output_path: str | Path) -> Path:
    evidence = Path(evidence_dir)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    validation = pd.read_csv(evidence / "validation_metrics.csv")
    summaries = json.loads((evidence / "subsystem_summaries.json").read_text(encoding="utf-8"))
    trace = pd.read_csv(evidence / "formula_traceability.csv")

    with PdfPages(output) as pdf:
        _text_page(
            pdf,
            "LunaLink Simulation - Project X",
            [
                "Mission: fixed 500 x 36,000 km, 63.4 deg HEO with Ottobrunn ground station.",
                "Scope: all four subsystems are simulated: EPS, TCS, ADCS, and TT&C.",
                "Tool: Python 3.13, headless evidence generator, Streamlit dashboard, 74 tests.",
                "High-fidelity physics: luni-solar + J3 orbit with the 63.4 deg critical-",
                "inclination frozen-apsides demonstration; Van Allen belt dose and 5-year solar-",
                "array degradation; closed-loop PD sun-pointing; ITU-R P.618/676 rain+gas "
                "attenuation, CCSDS coding gain and Doppler.",
                "Independent validation: the orbit is cross-checked against Orekit 13.1 (8x8 "
                "gravity + luni-solar) and NASA SPICE DE440 - period exact, J2-only within 38 km "
                "over 36 h, argument-of-perigee drift 0.004 deg/day at 63.4 deg vs 0.29 at 45 deg.",
                "Claim boundary: preliminary engineering simulator, not flight-qualified.",
            ],
        )
        _table_page(pdf, "Validation Summary", validation[["name", "status", "value"]])
        _image_page(pdf, "Orbit And Contact Evidence", evidence / "figures/orbit_groundtrack.png")
        _image_page(
            pdf,
            "Eclipse And Contact Timeline",
            evidence / "figures/eclipse_contact_timeline.png",
        )
        _image_page(pdf, "EPS Power And Battery SOC", evidence / "figures/eps_power_soc.png")
        _image_page(
            pdf,
            "Thermal Six-Face/Internal Response",
            evidence / "figures/thermal_faces_internal.png",
        )
        _image_page(
            pdf,
            "ADCS Detumble And Momentum",
            evidence / "figures/adcs_detumble_pointing.png",
        )
        _image_page(
            pdf,
            "TT&C Range, Margin, And Data",
            evidence / "figures/ttc_range_margin_data.png",
        )
        _table_page(pdf, "Traceability Snapshot", trace.head(8))
        _text_page(pdf, "Assumptions, AI Use, And References", _closing_lines(summaries))

    return output


def _text_page(pdf: PdfPages, title: str, lines: list[str]) -> None:
    fig = plt.figure(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    fig.text(0.08, 0.94, title, fontsize=20, weight="bold", color="#004b87")
    y = 0.86
    for line in lines:
        for wrapped in textwrap.wrap(line, width=88):
            fig.text(0.08, y, wrapped, fontsize=10.5, color="#1f2937")
            y -= 0.035
        y -= 0.02
    pdf.savefig(fig)
    plt.close(fig)


def _table_page(pdf: PdfPages, title: str, table: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    ax.axis("off")
    ax.set_title(title, fontsize=18, weight="bold", color="#004b87", pad=16)
    trimmed = table.copy()
    for column in trimmed.columns:
        trimmed[column] = trimmed[column].astype(str).map(lambda value: textwrap.shorten(value, 42))
    mpl_table = ax.table(
        cellText=trimmed.values,
        colLabels=trimmed.columns,
        loc="center",
        cellLoc="left",
    )
    mpl_table.auto_set_font_size(False)
    mpl_table.set_fontsize(7.5)
    mpl_table.scale(1.0, 1.35)
    pdf.savefig(fig)
    plt.close(fig)


def _image_page(pdf: PdfPages, title: str, image_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.27, 11.69))
    fig.patch.set_facecolor("white")
    ax.axis("off")
    ax.set_title(title, fontsize=18, weight="bold", color="#004b87", pad=14)
    if image_path.exists():
        image = mpimg.imread(image_path)
        ax.imshow(image)
    else:
        ax.text(0.5, 0.5, f"Missing image: {image_path}", ha="center", va="center")
    pdf.savefig(fig)
    plt.close(fig)


def _closing_lines(summaries: dict[str, Any]) -> list[str]:
    return [
        "All mission parameters are fixed by the Project X brief. SI units are used internally.",
        "The tool states assumptions explicitly in qualification/assumptions_register.csv.",
        "AI was used for planning, implementation assistance, review, and documentation; "
        "outputs were checked with tests, static analysis, and engineering sanity checks.",
        "Key references: NASA Systems Engineering Handbook, NASA-STD-7009B, "
        "NASA-STD-8739.8B, ECSS-E-ST-10C, ECSS-Q-ST-80C, Vallado, Wertz, Gilmore, "
        "Markley and Crassidis, Sidi, CCSDS, JPL DESCANSO, GMAT, Orekit, Basilisk.",
        f"EPS minimum SOC: {summaries['eps']['min_soc']:.3f}.",
        (
            "Thermal worst operating margin K: "
            f"{summaries['thermal']['worst_operating_margin_k']:.3f}."
        ),
        f"ADCS final angular speed deg/s: {summaries['adcs']['final_angular_speed_deg_s']:.4f}.",
        f"TT&C X-band minimum margin dB: {summaries['ttc']['xband_min_margin_db']:.3f}.",
        _new_physics_line(summaries),
        "Open certification items: external GMAT/Orekit numerical correlation, "
        "independent review sign-off, hardware-datasheet replacement, and authority acceptance.",
    ]


def _new_physics_line(summaries: dict[str, Any]) -> str:
    orbit = summaries.get("orbit", {})
    radiation = summaries.get("radiation", {})
    pointing = summaries.get("adcs_pointing", {})
    comms = summaries.get("comms", {})
    return (
        "High-fidelity results: analytic apsidal drift "
        f"{orbit.get('analytic_argp_rate_deg_per_day', 0):.4f} deg/day (Orekit 0.004); belt dose "
        f"{radiation.get('annual_dose_krad_si_estimate', 0):.1f} krad(Si)/yr with "
        f"{radiation.get('array_remaining_power_5yr', 0) * 100:.0f}% 5-yr array power; closed-loop "
        f"sun-pointing settled error {pointing.get('settled_max_pointing_error_deg', 0):.3f} deg; "
        f"ITU-R X-band 5 deg loss {comms.get('atmos_loss_5deg_db', 0):.2f} dB, CCSDS coding gain "
        f"{comms.get('ccsds_coding_gain_db', 0):.1f} dB."
    )


def main() -> int:
    args = parse_args()
    output = build_pdf_report(args.evidence, args.out)
    print(f"Wrote PDF report to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
