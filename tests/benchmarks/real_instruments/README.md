## Real-Instrument Benchmarks (Placeholders)

**Package version:** 3.7.0 (`soundspectranalyse`) — April 2026  

Add curated real-instrument WAV files here along with documented ground truth.
Each dataset should include:
- instrument name, note, dynamic
- recording conditions
- expected metric ranges (harmonic/inharmonic/subbass, fatness index)
- uncertainty bounds (e.g., ±2σ)

Suggested structure:
```
tests/benchmarks/real_instruments/
  dataset_manifest.json
  audio/
    instrument_note_dynamic.wav
```

This repository ships **placeholders only** (no copyrighted audio).

### Schema + Examples
- `manifest_schema.json`: JSON Schema for dataset manifests
- `manifest_examples.json`: Example entries for IOWA/McGill/Orchidea/Philharmonia
