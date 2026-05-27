## Tag Central

Tag Central is a desktop application for managing vessel tag data in a single canonical database, resolving import conflicts safely, and generating downstream batch export files for re-import workflows.

The application is implemented with Python and Tkinter, with a modular architecture that separates UI, domain, persistence, and synchronization logic.

## Features

- Import tag spreadsheets from `.csv`, `.xlsx`, and `.xls` files
- Normalize and validate imported data before merge
- Resolve tag/description conflicts through an interactive dialog
- Filter by vessel and search across tags, descriptions, and vessel names
- Rename existing tags from the UI
- Persist the canonical tag database to `tags.csv`
- Generate vessel export files in `exports/` with `old_tag` and `new_tag` mapping

## Project Structure

`main.py`  
Application entrypoint and window bootstrap.

`app_config.py`  
Centralized application constants and filesystem paths.

`app_controller.py`  
Main orchestration layer connecting UI events to business logic and persistence.

`models/tag_record.py`  
Domain entity for tag records.

`services/tag_repository.py`  
CSV persistence for loading/saving tags.

`services/spreadsheet_loader.py`  
Spreadsheet parsing and row normalization.

`services/tag_sync_service.py`  
Tag merge, conflict detection, and naming strategy logic.

`services/export_service.py`  
Export file generation for downstream systems.

`ui/main_window.py`  
Primary application interface and widget layout.

`ui/conflict_dialog.py`  
Conflict resolution dialog for imported rows.

## Requirements

- Python 3.11+ recommended
- A GUI-capable Python environment (Tkinter support enabled)

Install dependencies:

```bash
pip install -r requirements.txt
```

## Setup

1. Clone or download this repository.
2. Create and activate a virtual environment.
3. Install dependencies from `requirements.txt`.

Example:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the Application

```bash
python main.py
```

## Usage Guide

1. Launch the app.
2. Click `Import Spreadsheet`.
3. Choose a source file (`.csv`, `.xlsx`, or `.xls`).
4. Enter the vessel name.
5. If a conflict appears, choose one of:
   - `Use Imported Tag`
   - `Use Existing Tag`
   - `Keep Both (Suffix Imported)`
   - `Skip Row`
6. Review merged data in the table.
7. Use vessel filter and search to validate results.
8. Click `Save` to force a database save at any time.
9. Re-import generated export files from `exports/` into downstream systems as needed.

## Data Contract

### Input Spreadsheet

The importer expects these columns (case-sensitive):

- `Name` for tag name
- `Description` for tag description

Additional columns are preserved in export row payloads.

### Database File (`tags.csv`)

Columns:

- `tag_name`
- `description`
- `vessels` (semicolon-delimited)
- `row_data` (JSON-encoded row metadata)

### Export Files

Generated as:

`exports/<VESSEL>_BATCH_EXPORT.csv`

Each row includes:

- Original spreadsheet fields
- `old_tag`
- `new_tag`

## Error Handling

- Unsupported file types are rejected during import.
- Spreadsheet parse failures are reported in a modal error dialog.
- Invalid rename operations (empty or duplicate tags) are blocked with explicit feedback.
- Save and import errors are surfaced to the user with actionable messages.

## Design Principles Applied

- Single Responsibility: one class per file with clear boundaries
- Open/Closed: services can be extended without changing UI layout code
- Dependency Direction: controller depends on abstractions/services, UI remains focused on display
- DRY: import/export and persistence logic centralized in dedicated services
- Readability: PEP 8 naming, type hints, and concise method scopes

## Troubleshooting

- If Excel import fails, verify `openpyxl` is installed in your active environment.
- If the app does not launch, confirm Tkinter is available in your Python build.
- If no rows import, verify input files include non-empty `Name` and `Description` columns.

## Future Enhancements

- Automated unit tests for service layer
- Undo history for tag rename and merge actions
- Bulk conflict resolution workflows
- Dark/light theme toggle
