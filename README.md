## Tag Central

Tag Central is a desktop application for managing vessel tag data across **Proficy** and **Cimplicity**, keeping a single canonical database, resolving import conflicts safely, and generating Proficy batch export files for re-import.

Cimplicity is treated as the source of truth when linked: changes are applied to the Proficy side (exportable via CSV) so Cimplicity points rarely need manual edits.

## Features

- **Import Proficy** spreadsheets (`.csv`, `.xlsx`, `.xls`) with `Name` and `Description`
- **Import Cimplicity** Shared Name Files (`.csv` with `PT_ID`, `DESC`, `ADDR`)
- Address-first linking between programs (`%G00479` matches `%G0479`)
- Configurable tag alias rules (`alias_rules.json`, e.g. `ALM_` ↔ `ALARM_`)
- Sync status per tag: Synced, Proficy Only, Proficy Drift, Name Mismatch, Needs Align
- **Sync Dashboard** for drift and alignment overview
- **Cimplicity Review Queue** for unmatched Cimplicity-only points
- Proficy batch export via **Export Changes**
- Optional **Cimplicity manual work report** when a change must be done in Cimplicity
- Vessel filter, program filter, search, find/replace, conflict view, backups

## Project Structure

| Path | Role |
|------|------|
| `main.py` | Application entrypoint |
| `app_controller.py` | UI orchestration |
| `models/tag_record.py` | Canonical tag + dual-program fields |
| `models/program_snapshot.py` | Per-program snapshot metadata |
| `services/tag_repository.py` | Extended `tags.csv` persistence |
| `services/spreadsheet_loader.py` | Proficy import |
| `services/cimplicity_loader.py` | Cimplicity Shared Name File import |
| `services/address_normalizer.py` | Cross-program address matching |
| `services/tag_link_service.py` | Link Cimplicity rows to canonical tags |
| `services/cross_program_sync_service.py` | Cimplicity-wins sync policy |
| `services/cimplicity_review_queue.py` | Unmatched Cimplicity rows |
| `services/cimplicity_change_report.py` | Manual Cimplicity work CSV |
| `services/tag_alias_rules.py` | Prefix alias configuration |
| `ui/cimplicity_sync_dialog.py` | Bulk Cimplicity sync resolver |
| `ui/cimplicity_review_dialog.py` | Review queue UI |
| `ui/sync_dashboard_dialog.py` | Sync health dashboard |

## Requirements

- Python 3.11+ recommended
- Tkinter (GUI)
- `pandas`, `openpyxl` (see `requirements.txt`)

```bash
python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

## Usage

### Proficy import

1. **Import Proficy…** → select spreadsheet → enter vessel name.
2. Resolve description/tag conflicts in the Proficy conflict dialog if needed.
3. If a tag is already linked to Cimplicity, Proficy import updates the Proficy snapshot but **does not override** the canonical description (drift is flagged).

### Cimplicity import

1. **Import Cimplicity…** → select Shared Name File (e.g. export from Cimplicity 6.x) → enter vessel.
2. Rows are matched by `PT_ID`, normalized `ADDR`, or alias rules.
3. Actionable mismatches open the **Cimplicity Sync Resolver** (default: **Align Proficy to Cimplicity**).
4. Unmatched rows go to **Cimplicity Review** for later Proficy tag creation.
5. Queued changes appear on **Export Changes** as Proficy batch CSV files.

### Sync & review

- **Sync Dashboard…** — counts and tabs by sync status; align drift from Proficy to Cimplicity.
- **Cimplicity Review (N)** — create Proficy tags from queue items or dismiss.

### Filters

- **Vessel** — filter by vessel membership
- **Program** — All / Proficy only / Cimplicity only / Needs sync
- **Search** — text across tag, description, addresses, vessels

## Data Contract

### Proficy input

- Required: `Name`, `Description`
- Additional columns preserved in `proficy_row_data` JSON

### Cimplicity input

- Required: `PT_ID`, `DESC`
- `ADDR` used for linking; comment lines (`##`) are skipped automatically

### Database (`tags.csv`)

| Column | Purpose |
|--------|---------|
| `tag_name` | Canonical tag (Cimplicity `PT_ID` when linked) |
| `description` | Canonical description |
| `vessels` | Semicolon-delimited vessel list |
| `proficy_row_data` | Proficy export payload (JSON) |
| `cimplicity_row_data` | Cimplicity row snapshot (JSON) |
| `cimplicity_pt_id` | Cimplicity point ID |
| `proficy_name` | Last Proficy `Name` |
| `linked_address` | Normalized IO address |
| `sync_status` | Sync state code |
| `link_method` | How the link was established |
| `row_data` | Legacy alias of `proficy_row_data` (backward compatible) |

Legacy files with only `row_data` load as Proficy-only tags.

### Exports

- **Proficy:** `exports/<VESSEL>_BATCH_EXPORT.csv` (and `-N` suffix if file exists)
- **Cimplicity manual:** `exports/<VESSEL>_CIMPLICITY_MANUAL.csv` when flagged during import

## Configuration

`alias_rules.json` — prefix pairs for tag-name matching (e.g. `ALM_` / `ALARM_`).

## Tests

```bash
myenv/bin/python run_tests.py
```

## Troubleshooting

- Cimplicity import requires a true Shared Name File CSV (not Proficy format).
- If addresses do not link, check `ADDR` / `IOAddress` and review alias rules.
- Restart the app after code updates if an old process is still running.
