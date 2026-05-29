# Tag Central

Desktop app for managing vessel tags across **Proficy** and **Cimplicity**. One canonical database (`tags.csv`), Proficy batch export for re-import, and Cimplicity manual task tracking when HMI edits are required.

**Policy:** When linked, **Cimplicity is source of truth**; Proficy is updated via export CSV. Avoid bulk re-import of Cimplicity CSV after initial linking.

## Quick start

```bash
python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
python main.py
```

## Building installers

Branded builds bundle the **Tag Center** icon, version, and app metadata. Data is stored outside the app bundle:

| Platform | Tag database & backups | Export CSVs |
|----------|------------------------|-------------|
| macOS | `~/Library/Application Support/TagCenter/` | `<folder containing the app>/Exports/` (e.g. `~/Downloads/Exports/` if the `.app` is in Downloads) |
| Windows | `%APPDATA%\TagCenter\` | `<folder containing Tag Center.exe>/Exports/` |

### macOS (.app)

On a Mac, from the project root:

```bash
chmod +x build-mac.sh
./build-mac.sh
```

Output: `dist/Tag Center.app` (onedir bundle — fast startup, no one-file extract delay)

The app shows a **startup splash** immediately while modules and your tag database load. Pandas is loaded only when you import/export Excel files.

### Distributing on macOS (GitHub / email / USB)

When you build on your Mac and run the app locally, it works. After someone **downloads** the `.app` or `.zip` from the internet, macOS **Gatekeeper** blocks it unless the app is signed and **notarized** with an [Apple Developer](https://developer.apple.com) account ($99/year).

That produces messages like:

> The application “Tag Center” can’t be opened.

This is normal for unsigned PyInstaller apps. The app is not necessarily broken.

**For people installing your release:**

1. Unzip the download (double-click `Tag-Center-macOS.zip`).
2. **Do not** only double-click the app the first time.
3. **Right-click** `Tag Center.app` → **Open** → **Open** in the dialog (confirms you trust it once).
4. Or remove the download quarantine flag in Terminal:

```bash
xattr -dr com.apple.quarantine ~/Downloads/Tag\ Center.app
```

Then open normally. You can also use **System Settings → Privacy & Security → Open Anyway** if macOS shows a blocked-app banner.

**For maintainers:**

| Step | Purpose |
|------|---------|
| `./build-mac.sh` | Builds, ad-hoc signs, creates `dist/Tag-Center-macOS.zip` |
| Upload `Tag-Center-macOS.zip` to GitHub Releases | Preserves executable bits better than zipping in Finder |
| Apple Developer ID + `notarytool` + staple | Required for “just double-click” on most Macs without warnings |

Renaming the app (e.g. to `Tag Center Mac.app`) is fine; keep the bundle name in release notes so users know what to open.

### Windows (.exe)

On Windows, from the project root in PowerShell:

```powershell
.\build-windows.ps1
```

Or double-click `build-windows.bat`.

Output: `dist\Tag Center\Tag Center.exe` (onedir folder — copy the whole `Tag Center` folder to distribute)

### Icons

Source artwork: `assets/logo-1024.png`. Regenerate platform icons with:

```bash
pip install pillow
python scripts/generate_icons.py
```

## Typical workflow

1. **Import Proficy** — preview dry-run summary, then apply. Resolve import conflicts if prompted.
2. **Import Cimplicity** — preview link stats, resolve sync dialog, then review the **link report**.
3. **Cimplicity Review** — create Proficy tags for unmatched points (queued for export).
4. **Review Export Queue** — verify pending Proficy rows before export.
5. **Export Proficy Changes** — write per-vessel batch CSVs; optionally **validate** files.
6. **Cimplicity Tasks** — complete manual Cimplicity edits and check off tasks.

## Main features

| Feature | Description |
|--------|-------------|
| Import Proficy / Cimplicity | Separate imports with **dry-run preview** before apply |
| Cimplicity link report | Post-import breakdown: match by PT_ID, address, alias, ambiguous, review queue |
| Export queue inspector | Review, edit, or remove pending Proficy export rows |
| Export validation | After export, compare CSV to queued Name/Description/Address |
| Internal mismatches | Filter **View Internal Mismatches**; groups **G** (same description), **A** (same address, different descriptions), **P** (same address + PT_ID prefix family) |
| Tag diff | Context menu **View Tag Diff** — canonical vs Proficy vs Cimplicity |
| Merge tags | Select two tags → **Merge Tags…** (one survivor, one Proficy export) |
| **Documentation** | **Documentation** button — IO lists, alarm lists, tag dictionary, commissioning, network map, operator manual, change log → HTML dashboard, Excel, CSV, Word |
| Align / increment | Align to Cimplicity; increment descriptions for **G** groups |
| Auto-backup | Before large bulk actions (review create/dismiss all, big deletes, large imports) |
| Backups | Manual backup/restore page |

## Filters

- **Vessel** — membership filter  
- **Program** — All / Proficy only / Cimplicity only / Needs sync  
- **Search** — tag, description, address, vessels  
- **View Internal Mismatches** — auto-sorts by group; restores prior sort when unchecked  

## Data files

| File | Purpose |
|------|---------|
| `tags.csv` | Canonical tag database |
| `cimplicity_review_queue.json` | Unmatched Cimplicity rows |
| `cimplicity_manual_tasks.json` | Manual Cimplicity work checklist |
| `alias_rules.json` | Prefix alias pairs for linking |
| `backups/` | DB and JSON snapshots |
| **`Exports/`** next to the app | Proficy batch CSVs and Cimplicity manual reports (e.g. `Downloads/Exports` when the `.app` is in Downloads) |
| **`Documentation/`** in the app folder | Auto-generated docs under `Documentation/TagCentral_YYYYMMDD_HHMMSS/` (e.g. `Tag Central/Documentation/` when running from source) |

### Proficy import columns

Required: `Name`, `Description`. Extra columns kept in `proficy_row_data`.

### Cimplicity import columns

Required: `PT_ID`, `DESC`. `ADDR` used for address linking. `##` comment lines skipped.

### `tags.csv` columns

`tag_name`, `description`, `vessels`, `proficy_row_data`, `cimplicity_row_data`, `cimplicity_pt_id`, `proficy_name`, `linked_address`, `sync_status`, `link_method`

## Sync statuses

| Status | Meaning |
|--------|---------|
| Synced | Canonical matches linked Cimplicity |
| Proficy Only | No Cimplicity link |
| Proficy Drift | Description differs from Cimplicity |
| Name Mismatch | Proficy name ≠ Cimplicity PT_ID |
| Needs Align | Linked but Proficy not fully aligned |

## Tests

```bash
myenv/bin/python run_tests.py
```

Includes unit tests and small golden fixtures under `tests/fixtures/`.

## Project layout

| Path | Role |
|------|------|
| `main.py` | Entry point |
| `app_controller.py` | UI orchestration |
| `services/cross_program_sync_service.py` | Cimplicity-wins sync |
| `services/export_queue_service.py` | Pending Proficy export queue |
| `services/internal_mismatch_service.py` | G/A/P mismatch groups |
| `services/proficy_import_analyzer.py` | Proficy dry-run |
| `services/tag_merge_service.py` | Merge two tags |
| `services/export_validation_service.py` | Post-export CSV check |
| `ui/export_queue_dialog.py` | Export queue inspector |
| `ui/import_dry_run_dialog.py` | Import preview |
| `ui/cimplicity_link_report_dialog.py` | Link report |
| `ui/tag_diff_dialog.py` | Proficy vs Cimplicity diff |
