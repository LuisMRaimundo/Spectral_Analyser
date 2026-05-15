#!/usr/bin/env python3
"""
Isolation entry for Stage 2 when t-SNE / UMAP / anomaly flags are enabled from the Tk GUI.

``pipeline_orchestrator_gui`` may spawn ``sys.executable gui_compile_stage2_worker.py CONFIG.json``
so native crashes in numba/UMAP or heavy sklearn paths do not terminate the GUI process.

CONFIG.json format:
  {"kwargs": { ... keyword args for compile_metrics.compile_density_metrics_with_pca ... },
   "pickle_out": "path/to/write/compiled_df.pkl" }
"""
from __future__ import annotations

import json
import pickle
import sys
import traceback
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: gui_compile_stage2_worker.py CONFIG.json", file=sys.stderr)
        return 2

    cfg_path = Path(sys.argv[1])
    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    kwargs = payload["kwargs"]
    pickle_out = Path(payload["pickle_out"])

    root = Path(__file__).resolve().parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import matplotlib

    matplotlib.use("Agg", force=True)

    import compile_metrics

    df = compile_metrics.compile_density_metrics_with_pca(**kwargs)
    pickle_out.parent.mkdir(parents=True, exist_ok=True)
    pickle_out.write_bytes(pickle.dumps(df, protocol=pickle.HIGHEST_PROTOCOL))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
