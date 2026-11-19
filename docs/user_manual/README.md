# TechPulse User Training Manual

**Version:** 1.2 · 18 November 2026

- [Open the PDF manual](TechPulse_User_Training_Manual.pdf)
- [Download the editable Word manual](TechPulse_User_Training_Manual.docx)
- [Read the final QA report](USER_MANUAL_QA_REPORT.md)

The manual covers the application workflow, data-quality messages, Synthetic demonstration limits, and the current Research evidence gaps. The screenshots are retained under `screenshots/`; the builder and Word export script are included for reproducibility.

## Compatibility note

This manual was produced from the TechPulse application version included on the `codex/techpulse-manual-v1.2` review branch. The repository's `main` branch remains unchanged until this branch is reviewed and merged. Merge the application and manual together so their versions stay aligned.

## Rebuild

From the repository root, run `python docs/user_manual/build_manual.py`. Then, on Windows with Microsoft Word installed, run `powershell -ExecutionPolicy Bypass -File docs/user_manual/refresh_export.ps1` to refresh generated page references and export the PDF.
