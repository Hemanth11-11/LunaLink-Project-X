# Certification Readiness Matrix

## Claim Boundary

LunaLink is a preliminary engineering simulation and Project X submission tool.
This matrix prepares the tool for a future NASA/ESA-style review. It is not a
certificate, qualification statement, operational approval, or flight acceptance.

## Readiness Status

| Area | NASA/ECSS-style expectation | Current evidence | Status |
| --- | --- | --- | --- |
| Requirements baseline | Requirements identified, versioned, and traceable | `requirements_baseline.md`, `formula_traceability.csv` | Ready for review |
| Assumptions | Engineering assumptions explicitly stated and justified | `assumptions_register.csv`, dashboard Evidence tab | Ready for review |
| Model credibility | Model purpose, assumptions, validation, uncertainty, and limitations documented per NASA-STD-7009B intent | `model_validation_report.md`, `model_limitations.md`, validation metrics | Partially ready |
| Verification | Repeatable automated tests and static checks | pytest suite, Ruff config, `verification_control_document.md` | Ready for academic review |
| Validation | Comparison against independent truth-style tools | GMAT/Orekit exports and validation recipe | Pending external run |
| Configuration control | Versioned artifacts with hashes and release index | `configuration_index.json` | Ready for controlled baseline |
| Software assurance | Coding standard, test evidence, nonconformance tracking | Ruff, pytest, `nonconformance_log.csv` | Partially ready |
| Tool qualification | Intended use, operational envelope, known limitations, acceptance criteria | qualification folder and report | Partially ready |
| Review independence | Independent technical review by non-author | `independent_review_checklist.md` prepared | Pending reviewer sign-off |
| Authority acceptance | Responsible technical authority approves use for a mission phase | Not applicable to this student project | Pending external authority |

## Minimum Evidence Needed Before Any Certified/Flight Use

1. Execute GMAT or Orekit cross-correlation for orbit period, altitude envelope,
   ground contacts, and eclipse events.
2. Record accepted tolerances and reviewer sign-off.
3. Freeze requirements, assumptions, code, data, and environment under formal
   configuration control.
4. Add independent code review records and nonconformance disposition.
5. Add uncertainty/sensitivity results for all critical margins.
6. Replace representative subsystem values with selected hardware datasheets.
7. Run robustness tests across edge cases and off-nominal parameter ranges.
8. Approve the tool's intended use and limitations with a responsible authority.

## Certification-Readiness Score

Current local evidence package: strong for an academic/preliminary engineering
review, incomplete for formal certification because independent validation and
authority acceptance cannot be self-produced.
