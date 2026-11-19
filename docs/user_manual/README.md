# TechPulse User Training Manual

**Version:** 1.2 · 18 November 2026

- [Open the PDF manual](TechPulse_User_Training_Manual.pdf)
- [Download the editable Word manual](TechPulse_User_Training_Manual.docx)
- [Read the final QA report](USER_MANUAL_QA_REPORT.md)

The manual covers the application workflow, data-quality messages, Synthetic demonstration limits, and the current Research evidence gaps. The screenshots are retained under `screenshots/`; the builder and Word export script are included for reproducibility.

## Compatibility note

This manual was produced from the local TechPulse application copy inspected for the project. Its dashboard files differ from the files currently on the GitHub `main` branch. Review that version difference before merging the manual into `main` or treating it as instructions for the application currently on `main`.

## Rebuild

From the repository root, run `python docs/user_manual/build_manual.py`. Then, on Windows with Microsoft Word installed, run `powershell -ExecutionPolicy Bypass -File docs/user_manual/refresh_export.ps1` to refresh generated page references and export the PDF.
