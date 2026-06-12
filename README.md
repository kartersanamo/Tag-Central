# Tag Central

Desktop app for managing vessel tags across **Proficy** and **Cimplicity**. One canonical database, Proficy batch export for re-import, and Cimplicity manual task tracking.

**Sync policy:** When linked, Cimplicity is source of truth. Proficy is updated via export CSV. Avoid bulk re-import of Cimplicity CSV after initial linking.

---

## Features

- **Import Proficy** — Excel/CSV with dry-run preview, conflict resolver, missing-description review
- **Import Cimplicity** — CSV linking by PT_ID, address, and alias rules; sync resolver; link report
- **Tag table** — Sort, filter by vessel/program/search, internal mismatch groups (G/A/P), array expand/collapse
- **Find & replace** — Inline filter, preview, apply, or delete matching tags
- **Edit / add / delete / merge tags** — Vessel membership, align to Cimplicity, increment descriptions
- **Export queue** — Review, edit, and remove pending Proficy rows before export
- **Export Proficy changes** — Per-vessel batch CSVs; post-export validation
- **Cimplicity review queue** — Create Proficy tags for unmatched Cimplicity points
- **Cimplicity manual tasks** — Checklist for HMI edits that cannot be exported
- **Documentation** — IO lists, alarm lists, tag dictionary, change log, commissioning, network map, operator manual → HTML, Excel, CSV, Word
- **Backups** — Manual snapshots, restore, revert pre-load backup
- **Context menu** — Edit, copy, align, array toggle, jump to mismatches, tag diff, merge

---

## Download

1. Open [GitHub Releases](https://github.com/YOUR_ORG/tag-central/releases) (replace with your repo URL).
2. **macOS:** Download `Tag-Central-macOS.zip`, unzip, right-click **Tag Central.app** → **Open** → **Open** (first launch only — unsigned app).
3. **Windows:** Download the `Tag Central` folder zip, unzip, run `Tag Central.exe`.

### Data locations

| What | Where |
|------|--------|
| Database & backups | macOS: `~/Library/Application Support/TagCentral/` · Windows: `%APPDATA%\TagCentral\` |
| Export CSVs | `<folder containing the app>/Exports/` |
| Documentation | `<folder containing the app>/Documentation/TagCentral_<timestamp>/` |

**Upgrading from "Tag Center":** Move `~/Library/Application Support/TagCenter/` to `TagCentral/` manually (macOS) or rename `%APPDATA%\TagCenter\` to `TagCentral\` (Windows).

---

## Run from source

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Requires Python 3.10+ and system **tkinter** (included with most Python installs).

---

## CLI (headless)

Every GUI capability is available without starting the window. Use `--cli` before the subcommand:

```bash
python main.py --cli status
python main.py --cli tags list --format json
python main.py --cli tags show PUMP01
python main.py --cli export queue list
python main.py --cli backup list
python main.py --cli cimplicity review list
```

**Packaged app:**

```bash
# macOS
"Tag Central.app/Contents/MacOS/Tag Central" --cli tags list

# Windows
"Tag Central.exe" --cli import proficy --file ship.xlsx --vessel C-LEGACY --yes
```

### Common commands

| Command | Purpose |
|---------|---------|
| `status` | Pending exports, review queue, manual tasks |
| `tags list/show/diff/add/edit/delete/merge/align/increment/copy` | Tag table operations |
| `tags find-replace --find X [--replace Y] [--apply\|--delete] --yes` | Bulk find/replace |
| `import proficy --file PATH --vessel NAME [--yes]` | Proficy import |
| `import cimplicity --file PATH --vessel NAME [--yes]` | Cimplicity import |
| `export run [--validate] --yes` | Write Proficy batch CSVs |
| `export queue list/remove/edit` | Inspect export queue |
| `backup list/create/restore/delete/revert` | Backup management |
| `docs generate --types io_list,... --formats html,excel --yes` | Documentation package |
| `cimplicity review list/create-proficy/dismiss` | Review queue |
| `cimplicity tasks list/toggle/clear-done` | Manual Cimplicity tasks |

### Import policy flags (no prompts)

| Flag | Values | Default |
|------|--------|---------|
| `--yes` | Apply after dry-run preview | off |
| `--conflict-action` | `skip`, `use_imported`, `use_existing`, `keep_both` | `skip` |
| `--sync-action` | `align_proficy`, `link_only`, `flag_manual_cimplicity`, `skip` | `skip` |
| `--ambiguous-action` | `align_selected`, `merge_then_align`, `link_only_selected`, `flag_manual_cimplicity`, `skip` | `skip` |
| `--descriptions` | `auto` (suggest), `fail` (abort if missing) | `auto` |

Global flags: `--format table|json`, `--quiet`

Exit codes: `0` success, `1` error, `2` policy abort (e.g. `--descriptions fail` with missing descriptions).

---

## Build from source

```bash
pip install -r requirements-build.txt
./build-mac.sh              # macOS → dist/Tag Central.app + Tag-Central-macOS.zip
.\build-windows.ps1         # Windows → dist\Tag Central\Tag Central.exe
```

Icons are generated from `assets/logo-1024.png` via `python scripts/generate_icons.py`.

---

## Tests

```bash
python run_tests.py
```

---

## Project layout

| Path | Role |
|------|------|
| `main.py` | Entry point |
| `core/` | Headless `TagCentralApp` business logic |
| `cli/` | `--cli` argparse commands |
| `controllers/` | UI orchestration (split by feature) |
| `services/` | Import, sync, export, backup, documentation logic |
| `models/` | Tag records and DTOs |
| `ui/` | Windows and dialogs |
