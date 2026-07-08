"""Markdown report builder for LunaLink evidence bundles."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .io import ensure_directory


def build_markdown_report(evidence_dir: str | Path, output_path: str | Path) -> Path:
    """Build a concise engineering report from a completed evidence directory."""

    evidence = Path(evidence_dir)
    output = Path(output_path)
    ensure_directory(output.parent)

    manifest = _read_json(evidence / "run_manifest.json")
    summaries = _read_json(evidence / "subsystem_summaries.json")
    validation = pd.read_csv(evidence / "validation_metrics.csv")
    trade = _read_optional_csv(evidence / "trade_results.csv")
    traceability = _read_optional_csv(evidence / "formula_traceability.csv")
    qualification_dir = Path("qualification")
    limitations = _read_optional_text(qualification_dir / "model_limitations.md")
    nonconformance = _read_optional_csv(qualification_dir / "nonconformance_log.csv")
    manifest_figures = manifest.get("figures", {})

    lines = [
        "# LunaLink Engineering Simulation Report",
        "",
        "## Scope",
        "",
        (
            "This report summarizes the Python evidence bundle for the LunaLink project "
            "brief: the fixed 500 x 36,000 km, 63.4 deg orbit and all four selected "
            "subsystems: EPS, TCS, ADCS, and TT&C."
        ),
        "",
        "The simulator is engineering-preliminary and NASA/ECSS-inspired. It is not "
        "flight-qualified, certified, or accepted for operations without formal IV&V, "
        "independent tool correlation, and authority approval.",
        "",
        "## Run Manifest",
        "",
        _bullet("Mode", manifest.get("mode", "unknown")),
        _bullet("J2 enabled", manifest.get("include_j2", "unknown")),
        _bullet("Critical validation failures", manifest.get("critical_failures", "unknown")),
        _bullet("Figure count", len(manifest_figures)),
        "",
        "## Validation Metrics",
        "",
        _markdown_table(validation[["name", "status", "value", "criterion", "source_module"]]),
        "",
        "## Subsystem Summary",
        "",
    ]

    for name, summary in summaries.items():
        lines.extend([f"### {name.upper()}", "", _summary_lines(summary), ""])

    if trade is not None and not trade.empty:
        ranked = trade.sort_values(
            ["unserved_energy_j", "min_soc"], ascending=[True, False]
        ).head(5)
        lines.extend(
            [
                "## EPS Design Trade",
                "",
                "The Pareto-style table ranks array/battery combinations by unserved energy "
                "and minimum state of charge.",
                "",
                _markdown_table(ranked),
                "",
            ]
        )

    if traceability is not None and not traceability.empty:
        lines.extend(
            [
                "## Formula And Requirement Traceability",
                "",
                _markdown_table(traceability),
                "",
            ]
        )

    lines.extend(
        [
            "## Artifact Hashes",
            "",
            _markdown_table(_artifact_hashes(evidence)),
            "",
        ]
    )

    if manifest_figures:
        lines.extend(["## Figures", ""])
        for figure_name, figure_path in manifest_figures.items():
            lines.append(f"- {figure_name}: `{figure_path}`")
        lines.append("")

    if nonconformance is not None and not nonconformance.empty:
        lines.extend(
            [
                "## Open Nonconformance Log",
                "",
                _markdown_table(nonconformance),
                "",
            ]
        )

    if limitations:
        lines.extend(
            [
                "## Model Limitations",
                "",
                _strip_heading(limitations),
                "",
            ]
        )

    lines.extend(
        [
            "## Evidence Files",
            "",
            "- Mission and subsystem time histories are stored as CSV files.",
            "- Scenario exports are stored under `scenario_exports/`.",
            "- Figures are stored under `figures/`.",
            "- Formula traceability is stored in `formula_traceability.csv`.",
            "",
            "## Core References",
            "",
            "- NASA/SP-2016-6105 Rev 2, NASA Systems Engineering Handbook.",
            "- NASA-STD-8739.8B, Software Assurance and Software Safety Standard.",
            "- ECSS-E-ST-10C, Space Engineering - System engineering general requirements.",
            "- ECSS-Q-ST-80C, Space Product Assurance - Software product assurance.",
            "- Vallado, Fundamentals of Astrodynamics and Applications.",
            "- Wertz, Space Mission Analysis and Design.",
            "- Gilmore, Spacecraft Thermal Control Handbook.",
            "- CCSDS Radio Frequency and Modulation Systems recommendations.",
            "",
        ]
    )

    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return pd.read_csv(path)


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _bullet(label: str, value: Any) -> str:
    return f"- {label}: `{value}`"


def _summary_lines(summary: dict[str, Any]) -> str:
    items = []
    for key, value in summary.items():
        if isinstance(value, float):
            items.append(f"- {key}: `{value:.6g}`")
        else:
            items.append(f"- {key}: `{value}`")
    return "\n".join(items)


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = []
    for _, row in frame.iterrows():
        cells = [_format_cell(row[column]) for column in columns]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, separator, *rows])


def _artifact_hashes(evidence: Path) -> pd.DataFrame:
    rows = []
    for name in [
        "run_manifest.json",
        "validation_metrics.csv",
        "subsystem_summaries.json",
        "formula_traceability.csv",
        "mission_timeseries.csv",
        "eps_timeseries.csv",
        "thermal_timeseries.csv",
        "adcs_timeseries.csv",
        "ttc_timeseries.csv",
    ]:
        path = evidence / name
        if path.exists():
            rows.append({"artifact": name, "sha256": _sha256(path)})
    return pd.DataFrame(rows)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strip_heading(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).strip()
    return text


def _format_cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    text = str(value)
    return text.replace("|", "/")
