# Deprecated Pipeline Package

`ml_pipeline/` is retained only for historical reference. The canonical TechPulse
workflow is now:

```text
python pipeline/run_pipeline.py
```

Do not use `ml_pipeline/` for academic results. It was an earlier query-output
prototype and does not implement the current temporal target construction,
chronological validation, provenance manifest, or evaluation warnings.
