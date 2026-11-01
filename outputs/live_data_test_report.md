# TechPulse live-data validation report

Date: 1 November 2026

## Test results

- Baseline before implementation: **26 passed, 2 warnings** in 57.83 seconds.
- Final run from the TechPulse repository root with the available Downloads test interpreter, `C:\Users\Administrator\Downloads\TechPulse-main (1)\TechPulse-main\.venv-test\Scripts\python.exe -m pytest tests/ -q`: **41 passed, 2 warnings** in 53.30 seconds.
- Both warnings are scikit-learn `X does not have valid feature names` warnings from the existing `tests/test_models.py::test_random_state_reproducibility` test.
- `compileall` succeeded for the new collectors, storage, page, scheduler and capture script. Both collector and scheduler `--help` commands ran successfully.
- The nine-page Streamlit `AppTest` smoke coverage passed without uncaught page exceptions.

## Real source collection

Collectors were executed against the actual public services for `mongodb`, which exists in the TechPulse catalogue and has explicit PyPI/npm mappings. Each source completed, and its observations were persisted through the runtime-configured TechPulse store. A subsequent read through `src.data_ingestion.load_external_observations()` returned **2,140 rows from four sources**.

| Source | Normalized rows added |
|---|---:|
| GitHub | 984 |
| Stack Exchange | 10 |
| PyPI | 178 |
| npm | 968 |
| **Total** | **2,140** |

The Edge screenshot shows the source statuses, actual metric snapshots, and a Stack Exchange recent-question time series. All nine application routes have browser screenshots in `outputs/live_data_screenshots/`; the contact sheet and route index are included there.

## Mocked coverage

`tests/test_live_data.py` exercises the GitHub, Stack Exchange, PyPI and npm response shapes, source pagination, missing/invalid API data, permanent and rate-limit HTTP responses, Stack Exchange backoff, unmapped packages, CSV fallback, duplicate identity handling, historical row preservation and SQLAlchemy insert/read/deduplication using temporary SQLite. The API tests do not require network access.

## Research boundary and limitations

- New API observations are stored separately from `data/feature_matrix.csv`, labels, model artifacts and historical evaluation; no training code consumes them.
- GitHub metrics use a bounded query-matched public repository sample. The 984 row count includes several metrics per repository; it is not a repository count.
- Stack Exchange recent question metrics are capped samples. The all-time tag count is source-reported, and question activity is a site-specific community signal rather than adoption.
- PyPI download statistics are not reported because PyPI's official JSON endpoint documents its `downloads` field as deprecated and always `-1`. npm last-month downloads are package requests, not unique users or production deployments.
- Package mappings are curated examples in `data/live_package_map.json`. Unmapped technology-registry pairs are skipped instead of guessed.
- No dedicated PostgreSQL integration-test database was used. SQLAlchemy persistence behavior was tested with SQLite; the live collection used the application's runtime-selected PostgreSQL or CSV store.
- Scheduler help and compilation were verified; the recurring 24-hour process was not left running after the validation session.
- Current stars, question counts and package download totals are collection-time measurements, not evidence that can be back-projected into the 2016–2018 training period.
