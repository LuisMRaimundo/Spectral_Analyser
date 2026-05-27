from __future__ import annotations

from pathlib import Path

import pandas as pd

from compile_metrics import _write_compiled_excel


def test_strict_aliases_written_to_legacy_aliases_sheet(tmp_path: Path) -> None:
    outp = tmp_path / "compiled.xlsx"
    df = pd.DataFrame(
        {
            "Note": ["A4"],
            "effective_partial_density": [1.23],
            "density_metric_raw": [1.23],
            "harmonic_density_component": [1.0],
            "inharmonic_density_component": [0.2],
            "subbass_density_component": [0.03],
            "harmonic_energy_ratio": [0.8],  # strict alias
            "inharmonic_energy_ratio": [0.18],  # strict alias
            "subbass_energy_ratio": [0.02],  # strict alias
        }
    )
    _write_compiled_excel(outp, df, metadata={})

    with pd.ExcelFile(outp) as xf:
        assert "Legacy_Aliases" in xf.sheet_names
        main_sheet = "Density_Metrics" if "Density_Metrics" in xf.sheet_names else "Compiled Metrics"
        main = xf.parse(main_sheet)
        aliases = xf.parse("Legacy_Aliases")

    assert "harmonic_energy_ratio" not in main.columns
    assert "inharmonic_energy_ratio" not in main.columns
    assert "subbass_energy_ratio" not in main.columns
    assert "harmonic_energy_ratio" in aliases.columns
