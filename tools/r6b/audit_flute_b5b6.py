"""R6b WP1 — flute B5/B6 census audit. Read-only; no formula changes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from validated_partials import resolve_subbass_member_mask

FLUTE = Path(r"D:\MADEIRAS\FLAUTA\IOWA_flute")
NOTES = [
    ("pp", "B5", FLUTE / r"IOWA_Flute_pp\_Sustains\analysis_results_v4.2.3\IOWA_flt_pp_B5_Sustains\B5\spectral_analysis.xlsx"),
    ("pp", "B6", FLUTE / r"IOWA_Flute_pp\_Sustains\analysis_results_v4.2.3\IOWA_flt_pp_B6_Sustains\B6\spectral_analysis.xlsx"),
    ("mf", "B6", FLUTE / r"IOWA_Flute_mf\_Sustains\analysis_results_v4.2.3\IOWA_flt_pp_B6_Sustains\B6\spectral_analysis.xlsx"),
    ("ff", "B6", FLUTE / r"IOWA_Flute_ff\_Sustains\analysis_results_v4.2.3\IOWA_flt_pp_B6_Sustains\B6\spectral_analysis.xlsx"),
]


def _neff_from_amps(amps) -> float:
    a = np.asarray([float(x) for x in amps if np.isfinite(float(x)) and float(x) > 0.0], dtype=float)
    if a.size == 0:
        return float("nan")
    p = a * a
    tot = float(np.sum(p))
    ss = float(np.sum(p * p))
    if ss <= 0.0:
        return 0.0
    return float((tot * tot) / ss)


def _truthy(s) -> bool:
    return str(s).strip().lower() in {"true", "1", "1.0"}


def _amp_col(df: pd.DataFrame) -> str | None:
    if "Amplitude_raw" in df.columns:
        return "Amplitude_raw"
    if "Amplitude" in df.columns:
        return "Amplitude"
    return None


def audit_one(dyn: str, note: str, path: Path) -> dict:
    if not path.is_file():
        # flute mf/ff folder names may use dots
        return {"dynamic": dyn, "note": note, "path": str(path), "error": "missing"}

    xls = pd.ExcelFile(path)
    hs = pd.read_excel(path, sheet_name="Harmonic Spectrum") if "Harmonic Spectrum" in xls.sheet_names else pd.DataFrame()
    ih = pd.read_excel(path, sheet_name="Inharmonic Spectrum") if "Inharmonic Spectrum" in xls.sheet_names else pd.DataFrame()
    sb = pd.read_excel(path, sheet_name="Sub-bass band") if "Sub-bass band" in xls.sheet_names else pd.DataFrame()
    met = pd.read_excel(path, sheet_name="Metrics").iloc[0] if "Metrics" in xls.sheet_names else None

    h_rows = []
    h_inc_amps = []
    if not hs.empty:
        ac = _amp_col(hs)
        for rec in hs.to_dict(orient="records"):
            inc = _truthy(rec.get("include_for_density"))
            amp = float(rec[ac]) if ac and pd.notna(rec.get(ac)) else float("nan")
            row = {
                "family": "H",
                "order": rec.get("Harmonic Number"),
                "freq_hz": rec.get("Frequency (Hz)", rec.get("extracted_frequency_hz")),
                "amp": amp,
                "snr_db": rec.get("snr_db"),
                "candidate_status": rec.get("candidate_status"),
                "include_for_density": inc,
                "exclusion_reason": rec.get("exclusion_reason"),
                "gate": rec.get("candidate_status"),
            }
            h_rows.append(row)
            if inc and np.isfinite(amp) and amp > 0:
                h_inc_amps.append(amp)

    i_rows = []
    i_all_amps = []
    i_confirmed_amps = []
    if not ih.empty:
        ac = _amp_col(ih)
        for rec in ih.to_dict(orient="records"):
            amp = float(rec[ac]) if ac and pd.notna(rec.get(ac)) else float("nan")
            status = str(rec.get("inharmonic_status") or "")
            confirmed = status in {"confirmed_inharmonic_partial", "confirmed_partial"}
            row = {
                "family": "I",
                "freq_hz": rec.get("Frequency (Hz)"),
                "amp": amp,
                "snr_db": rec.get("snr_db") if "snr_db" in rec else None,
                "inharmonic_status": status,
                "confirmation_failing_test": rec.get("confirmation_failing_test"),
                "include_for_density": confirmed,
                "gate": status or rec.get("Classification_Level"),
            }
            i_rows.append(row)
            if np.isfinite(amp) and amp > 0:
                i_all_amps.append(amp)
                if confirmed:
                    i_confirmed_amps.append(amp)

    s_rows = []
    s_member_amps = []
    if not sb.empty:
        ac = _amp_col(sb)
        mask, policy, excluded = resolve_subbass_member_mask(sb)
        if mask is None:
            mask = np.ones(len(sb), dtype=bool)
        for rec, keep in zip(sb.to_dict(orient="records"), mask):
            amp = float(rec[ac]) if ac and pd.notna(rec.get(ac)) else float("nan")
            row = {
                "family": "S",
                "freq_hz": rec.get("Frequency (Hz)"),
                "amp": amp,
                "membership": rec.get("subbass_membership"),
                "acoustic_status": rec.get("Acoustic_Interpretation_Status"),
                "include_for_density": bool(keep),
                "gate": rec.get("subbass_membership") or rec.get("Classification_Level"),
            }
            s_rows.append(row)
            if keep and np.isfinite(amp) and amp > 0:
                s_member_amps.append(amp)
    else:
        policy = "no_sheet"
        excluded = 0

    f012 = _neff_from_amps(h_inc_amps)
    f047 = _neff_from_amps(h_inc_amps + i_all_amps + s_member_amps)
    f047_confirmed_i = _neff_from_amps(h_inc_amps + i_confirmed_amps + s_member_amps)
    f047_h_only = _neff_from_amps(h_inc_amps)

    pipe_f012 = float(met["effective_partial_density"]) if met is not None else float("nan")
    pipe_f047 = float("nan")
    # compiled sheet lives one tree up; Metrics may not have F-047
    compiled = path.parents[2] / "compiled_density_metrics_research.xlsx"
    pipe_f047_compiled = float("nan")
    pipe_ewsd = float("nan")
    pipe_h = float("nan")
    if compiled.is_file():
        cdf = pd.read_excel(compiled, sheet_name="Spectral_Density_Metrics")
        hit = cdf[cdf["Note"].astype(str) == note]
        if not hit.empty:
            pipe_f047_compiled = float(hit.iloc[0]["note_effective_component_density"])
            pipe_ewsd = float(hit.iloc[0]["EWSD_score_acoustic_balanced"])
            pipe_h = float(hit.iloc[0]["validated_harmonic_component_count_body_ceiling"])

    resid = {}
    if met is not None:
        for k in (
            "residual_exclusion_footprint_bins",
            "peak_power_footprint_bins",
            "window_enbw_hz",
            "core_residual_energy_ratio",
            "residual_energy_ratio",
            "residual_region_hz_total",
            "estimated_snr_db",
            "harmonic_validated_count",
            "effective_partial_density",
            "f0_used_for_density_hz",
            "f0_fit_accepted",
            "f0_used_for_density_source",
        ):
            if k in met.index:
                resid[k] = met[k] if not isinstance(met[k], (np.floating, float)) or pd.notna(met[k]) else None
                if isinstance(resid[k], (np.floating, np.integer)):
                    resid[k] = float(resid[k])

    n_h_inc = len(h_inc_amps)
    n_i = len(i_all_amps)
    n_i_conf = len(i_confirmed_amps)
    n_s = len(s_member_amps)
    n_his = n_h_inc + n_i + n_s

    return {
        "dynamic": dyn,
        "note": note,
        "path": str(path),
        "census_H": h_rows,
        "census_I": i_rows,
        "census_S": [row for row in s_rows if row.get("include_for_density")],
        "census_S_n_listed": len(s_rows),
        "census_S_n_member": n_s,
        "subbass_policy": policy,
        "subbass_excluded": int(excluded),
        "n_H_include_for_density": n_h_inc,
        "n_I_all_rows": n_i,
        "n_I_confirmed": n_i_conf,
        "n_S_member": n_s,
        "n_HIS_F047_pool": n_his,
        "hand_F012_H_include": f012,
        "hand_F047_H_plus_I_all_plus_S": f047,
        "hand_F047_H_plus_I_confirmed_plus_S": f047_confirmed_i,
        "hand_F047_H_only": f047_h_only,
        "pipeline_F012_effective_partial_density": pipe_f012,
        "pipeline_F047_note_effective_component_density": pipe_f047_compiled,
        "pipeline_EWSD": pipe_ewsd,
        "pipeline_validated_H_body_ceiling": pipe_h,
        "match_F012": bool(np.isfinite(f012) and np.isfinite(pipe_f012) and abs(f012 - pipe_f012) < 1e-6),
        "match_F047": bool(
            np.isfinite(f047) and np.isfinite(pipe_f047_compiled) and abs(f047 - pipe_f047_compiled) < 1e-4
        ),
        "F012_le_nH": bool(np.isfinite(f012) and f012 <= n_h_inc + 1e-9),
        "F047_le_nHIS": bool(np.isfinite(f047) and f047 <= n_his + 1e-9),
        "F047_gt_validated_H": bool(np.isfinite(f047) and np.isfinite(pipe_h) and f047 > pipe_h),
        "residual_footprint": resid,
        "H_include_amps": h_inc_amps,
        "I_all_amps": i_all_amps,
        "S_member_amps": s_member_amps,
    }


def _fix_mf_ff_paths(items):
    out = []
    for dyn, note, path in items:
        if path.is_file():
            out.append((dyn, note, path))
            continue
        root = FLUTE / f"IOWA_Flute_{dyn}" / "_Sustains" / "analysis_results_v4.2.3"
        cands = list(root.glob(f"*B6*/{note}/spectral_analysis.xlsx"))
        out.append((dyn, note, cands[0] if cands else path))
    return out


def main() -> int:
    items = _fix_mf_ff_paths(NOTES)
    reports = [audit_one(d, n, p) for d, n, p in items]
    slim = []
    for r in reports:
        slim.append({k: r[k] for k in r if k not in {"census_H", "census_I", "H_include_amps", "I_all_amps", "S_member_amps"}})
        slim[-1]["census_H_n"] = len(r.get("census_H") or [])
        slim[-1]["census_I_n"] = len(r.get("census_I") or [])
        print(json.dumps(slim[-1], indent=2, default=str))
        print("----")
    dest = _REPO / "docs" / "validation" / "_r6b" / "flute_b5b6_audit.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(reports, indent=2, default=str), encoding="utf-8")
    print("wrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
