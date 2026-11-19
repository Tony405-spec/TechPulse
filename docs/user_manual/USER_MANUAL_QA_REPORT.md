# TechPulse User Training Manual — Final QA Report

- **QA date:** 18 November 2026
- **Manual version:** 1.2
- **Application inspected:** Local TechPulse application and project records

## Deliverables

- `TechPulse_User_Training_Manual.docx` — editable Word manual.
- `TechPulse_User_Training_Manual.pdf` — final PDF exported from the refreshed Word file.
- `build_manual.py` — reproducible manual content and layout builder.
- `refresh_export.ps1` — Word field refresh, typography enforcement, and PDF export procedure.
- `manual_page_manifest.json` — regenerated task/page source manifest.
- `screenshots/` — 27 original application screenshots and 27 annotated copies. The screenshots retain the application’s real interface colours.

## Changes made

- Revised task explanations and procedures to guide a first-time user directly, with expected screen results and plain-language interpretation.
- Rephrased backend and maintenance language that was not needed to operate the application. Kept the one local launch command because it is required to start TechPulse.
- Corrected the manual to preserve the exact visible Research warning: “No valid persisted predictions exist.”
- Removed a false “screenshot unavailable” message that appeared when a screenshot had already been included earlier in the guide.
- Set document text in all Word story areas, including generated contents and index fields, to black Times New Roman without changing the established size hierarchy.
- Set both tables to the plain `Table Grid` style with white cells, black text, and black borders.
- Kept A4 pages, the existing chapter structure, screenshots, captions, page numbering, and refreshed contents, figure list, table list, and index.
- Used natural task flow instead of adding forced page breaks to inflate the page count.

## Verification results

- Word 2021 reported **73 pages, 1,268 paragraphs, 27 inline images, and 253 fields** at final export.
- `pdfinfo` reports **73 A4 pages** (595.44 × 841.68 points); the PDF was exported directly from the refreshed Word document.
- The Word file and final PDF both report 73 pages. The PDF contains no blank pages. Only the intentionally sparse cover has fewer than 350 extracted text characters; every other page exceeds that threshold.
- All extracted PDF text uses Times New Roman variants (regular, bold, and bold italic). All extracted text characters, including headings, captions, headers, footers, and page numbers, are black (`#000000`).
- All **2 tables** use `Table Grid`; every inspected cell has a white or unset fill and black or default black borders. No coloured table fills or coloured text were detected.
- All **73 pages** were rasterized and reviewed in contact sheets for page flow, headings, tables, screenshots, captions, and footers. Screenshot colours are retained as application evidence.
- No screenshot-unavailable placeholders remain. The warning quoted above matches the application wording.
- The generated contents, list of figures (27 entries), list of tables (2 entries), 40-term glossary, and alphabetical index were refreshed in Word.
- The final manual has **73 pages**, seven pages below the approximate 80-page target. The content was kept at readable density rather than padded to reach an exact count.

## Research and application limits represented in the manual

- Research mode is connected to PostgreSQL in the inspected environment, but it has no validated feature snapshots, lifecycle labels, valid Research model run, Research predictions, or saved Research explanations.
- The Stack Exchange source contains 45,238 rows and remains blocked because two cumulative records fail plausibility checks. Its recorded checksum is retained in the manual; the source was not repaired or changed.
- The survey source contains 685 rows while the Research database contains 684. The 2024 category discrepancy is documented, not reconciled by guessing.
- Verified company–technology adoption evidence and verified Kenya-specific technology observations remain unavailable in Research mode.
- The populated Synthetic mode is explicitly described as fictional. Its saved model results and weak Declining-class recall are not presented as evidence that TechPulse predicts real technology decline.
- No application code, database, migration, or research data was changed as part of this manual update. No application test suite was run; verification here covers manual generation, Word/PDF formatting, and page layout only.

## Startup instructions documented

From the TechPulse project folder in PowerShell:

```powershell
python -m streamlit run dashboard/app.py --server.port 8501
```

Open `http://localhost:8501`. If the startup message gives a different local address, use that address instead.

## Details to confirm before formal submission

The title page and document-control table now identify Kitili Tony Kenga (24/03652) and supervisor Dr. Rufus Gireka, as supplied. Confirm with the supervisor how to present the original research objective alongside the current evidence gap, the blocked community source, and the lifecycle-label definition differences.
