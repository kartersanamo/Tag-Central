"""

    Author: Karter Sanamo
    Company: Edison Chouest Offshore
    Date Created: 05/26/2026
    Date Last Modified: 05/26/2026
    Description:
        Tag synchronization and conflict manager.

    Licensing:
        All of the code belongs to the ownership of the Author ("Karter
        Sanamo") listed above and the Company ("Edison Chouest Offshore")
        listed above. No other persons or entities are allowed to use this
        software without permission.

"""

import os
import csv
import json
import pandas as pd
import tkinter as tk

from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog


APP_TITLE = "Tag Central"

DATABASE_FILE = "tags.csv"
EXPORT_FOLDER = "exports"


class TagCentralApp:

    def __init__(self, root):

        self.root = root

        self.root.title(APP_TITLE)
        self.root.geometry("1100x700")
        self.root.minsize(900, 550)

        self.tags = {}
        self.conflict_dialog = None
        self.active_vessel_filter = None

        self.load_database()
        self.build_ui()
        self.refresh_table()
        self.update_vessel_filter_list()

    def load_database(self):

        self.tags = {}

        if not os.path.exists(DATABASE_FILE):
            return

        with open(
            DATABASE_FILE,
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                tag_name = row.get(
                    "tag_name",
                    ""
                ).strip().upper()

                if not tag_name:
                    continue

                vessels = set()

                if row.get("vessels"):
                    vessels = {
                        vessel.strip().upper()
                        for vessel in row["vessels"].split(";")
                        if vessel.strip()
                    }

                row_data = {}

                if row.get("row_data"):
                    try:
                        row_data = json.loads(row["row_data"])
                    except json.JSONDecodeError:
                        row_data = {}

                self.tags[tag_name] = {
                    "description": row.get("description", "").strip().upper(),
                    "vessels": vessels,
                    "row_data": row_data
                }

    def save_database(self):

        with open(
            DATABASE_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                "tag_name",
                "description",
                "vessels",
                "row_data"
            ])

            for tag_name, data in sorted(self.tags.items()):

                writer.writerow([
                    tag_name,
                    data["description"],
                    ";".join(sorted(data["vessels"])),
                    json.dumps(data.get("row_data", {}))
                ])

    def build_ui(self):

        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Button(
            top,
            text="Import Vessel Spreadsheet",
            command=self.import_spreadsheet
        ).pack(side="left", padx=5)

        ttk.Button(
            top,
            text="Save Database",
            command=self.save_database_manual
        ).pack(side="left", padx=5)

        ttk.Button(
            top,
            text="Refresh",
            command=self.refresh_table
        ).pack(side="left", padx=5)

        ttk.Label(
            top,
            text="Vessel Filter:"
        ).pack(side="left", padx=(20, 5))

        self.vessel_var = tk.StringVar()
        self.vessel_combo = ttk.Combobox(
            top,
            textvariable=self.vessel_var,
            state="readonly",
            width=25
        )
        self.vessel_combo.pack(side="left", padx=5)
        self.vessel_combo.bind("<<ComboboxSelected>>", self.apply_vessel_filter)

        ttk.Button(
            top,
            text="Reset Filter",
            command=self.reset_vessel_filter
        ).pack(side="left", padx=5)

        ttk.Label(
            top,
            text="Search:"
        ).pack(side="left", padx=(20, 5))

        self.search_var = tk.StringVar()

        search_entry = ttk.Entry(
            top,
            textvariable=self.search_var,
            width=30
        )
        search_entry.pack(side="left")
        search_entry.bind("<KeyRelease>", self.search_tags)

        columns = ("tag_name", "description", "vessels")

        table_frame = ttk.Frame(self.root)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label="Change Tag", command=self.change_selected_tag)

        # FIX: restored missing method binding support
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.tree.heading("tag_name", text="Tag Name")
        self.tree.heading("description", text="Description")
        self.tree.heading("vessels", text="Vessels")

        self.tree.column("tag_name", width=200)
        self.tree.column("description", width=250)
        self.tree.column("vessels", width=500)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.status_var = tk.StringVar()
        self.status_var.set("0 Tags")

        status_bar = ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            padding=(10, 5)
        )
        status_bar.pack(fill="x")

    # FIX: restored missing context menu method
    def show_context_menu(self, event):

        item = self.tree.identify_row(event.y)

        if item:

            self.tree.selection_set(item)

            self.menu.post(
                event.x_root,
                event.y_root
            )

    def save_database_manual(self):

        try:
            self.save_database()
            messagebox.showinfo("Saved", "Database saved successfully.")
        except Exception as error:
            messagebox.showerror("Save Error", str(error))

    def get_all_vessels(self):

        vessels = set()
        for data in self.tags.values():
            vessels |= set(data["vessels"])
        return sorted(vessels)

    def update_vessel_filter_list(self):

        vessels = self.get_all_vessels()
        values = ["ALL"] + vessels
        self.vessel_combo["values"] = values

        if not self.vessel_var.get():
            self.vessel_combo.set("ALL")
            self.active_vessel_filter = None

    def apply_vessel_filter(self, event=None):

        value = self.vessel_var.get()

        if value == "ALL" or not value:
            self.active_vessel_filter = None
        else:
            self.active_vessel_filter = value

        self.refresh_table()

    def reset_vessel_filter(self):

        self.vessel_var.set("ALL")
        self.active_vessel_filter = None
        self.refresh_table()

    def search_tags(self, event=None):
        self.refresh_table()

    def refresh_table(self):

        text = self.search_var.get().strip().lower()

        self.tree.delete(*self.tree.get_children())

        count = 0

        for tag_name, data in sorted(self.tags.items()):

            if self.active_vessel_filter:
                if self.active_vessel_filter not in data["vessels"]:
                    continue

            vessels_text = ", ".join(sorted(data["vessels"]))

            if (
                text in tag_name.lower()
                or text in data["description"].lower()
                or text in vessels_text.lower()
            ):

                self.tree.insert(
                    "",
                    "end",
                    values=(tag_name, data["description"], vessels_text)
                )
                count += 1

        self.status_var.set(f"{count} Tags")

    def import_spreadsheet(self):
        filepath = filedialog.askopenfilename(
            title="Select Spreadsheet",
            filetypes=[
                ("Supported Files", "*.xlsx *.xls *.csv"),
                ("CSV Files", "*.csv"),
                ("Excel Files", "*.xlsx *.xls")
            ]
        )

        if not filepath:
            return

        vessel = simpledialog.askstring(
            "Vessel Name",
            "Enter vessel name:"
        )

        if not vessel:
            return

        vessel = vessel.strip().upper()

        try:

            ext = os.path.splitext(filepath)[1].lower()

            if ext in [".xlsx", ".xls"]:
                df = pd.read_excel(filepath, dtype=str)
            else:
                df = pd.read_csv(filepath, encoding="utf-8-sig", dtype=str)

            df.columns = df.columns.str.strip()

        except Exception as error:
            messagebox.showerror("Import Error", str(error))
            return

        exports = {}

        def add_export(vessel_key, old_tag, new_tag, row):

            exports.setdefault(vessel_key, [])
            exports[vessel_key].append({
                "old_tag": old_tag,
                "new_tag": new_tag,
                "row": row
            })

        for _, row in df.iterrows():

            row_data = {
                k: ("" if pd.isna(v) else str(v).strip())
                for k, v in row.to_dict().items()
            }

            imported_tag = row_data.get("Name", "").strip().upper()
            description = row_data.get("Description", "").strip().upper()

            if not imported_tag or not description:
                continue

            existing_match = None

            for t, d in self.tags.items():

                if not t or not d.get("description"):
                    continue

                if t == imported_tag or d["description"] == description:
                    existing_match = t
                    break

            conflict = existing_match is not None and (
                existing_match != imported_tag
                or self.tags.get(imported_tag, {}).get("description", "") != description
            )

            if conflict:

                result = self.resolve_conflict(
                    imported_tag,
                    description,
                    vessel
                )

                action = result.get("action", "skip")

                if action == "skip":
                    continue

                if action == "use_tag":

                    self.tags[imported_tag] = {
                        "description": description,
                        "vessels": {vessel},
                        "row_data": row_data
                    }

                    add_export(vessel, imported_tag, imported_tag, row_data)

                elif action == "use_existing":

                    target = result["existing_tag"]

                    if target in self.tags:
                        self.tags[target]["vessels"].add(vessel)

                    add_export(vessel, imported_tag, target, row_data)

                elif action == "keep_both":

                    new_desc = result["new_description"]
                    new_tag = imported_tag + "_2"

                    self.tags[new_tag] = {
                        "description": new_desc,
                        "vessels": {vessel},
                        "row_data": row_data
                    }

                    add_export(vessel, imported_tag, new_tag, row_data)

                elif action == "import_both":
                    self.tags[imported_tag] = {
                        "description": imported_desc,
                        "vessels": {vessel},
                        "row_data": row_data
                    }

                    if existing_tag in self.tags:
                        self.tags[existing_tag]["vessels"].add(vessel)

                    add_export(vessel, imported_tag, imported_tag, row_data)

            else:

                self.tags[imported_tag] = {
                    "description": description,
                    "vessels": {vessel},
                    "row_data": row_data
                }

                add_export(vessel, imported_tag, imported_tag, row_data)

        self.save_database()
        self.refresh_table()
        self.update_vessel_filter_list()
        self.write_exports(exports)

    def resolve_conflict(self, tag, description, vessel):

        win = tk.Toplevel(self.root)
        win.title("Conflict Resolver")
        win.geometry("900x650")
        win.transient(self.root)
        win.grab_set()

        result = {
            "action": "skip"
        }

        tk.Label(
            win,
            text=(
                f"Conflict found during import from vessel '{vessel}' between "
                f"TAG '{tag}' and DESCRIPTION '{description}' against existing database entries."
            ),
            font=("Arial", 11, "bold"),
            wraplength=850,
            justify="left"
        ).pack(pady=10)

        container = ttk.Frame(win)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = tk.Frame(container, bd=2, relief="groove", bg="#ffdddd")
        right_frame = tk.Frame(container, bd=2, relief="groove", bg="#ffdddd")

        left_frame.pack(side="left", fill="both", expand=True, padx=5)
        right_frame.pack(side="right", fill="both", expand=True, padx=5)

        tk.Label(left_frame, text="IMPORTED", font=("Arial", 10, "bold"), bg="#ffdddd").pack(pady=5)
        tk.Label(right_frame, text="EXISTING", font=("Arial", 10, "bold"), bg="#ffdddd").pack(pady=5)

        imported_tag_var = tk.StringVar(value=tag)
        imported_desc_var = tk.StringVar(value=description)

        existing_tag_match = None
        existing_desc_match = ""

        for t, d in self.tags.items():
            if not t or not d.get("description"):
                continue

            if t == tag or d["description"] == description:
                existing_tag_match = t
                existing_desc_match = d["description"]
                break

        existing_tag_var = tk.StringVar(value=existing_tag_match or "")
        existing_desc_var = tk.StringVar(value=existing_desc_match or "")

        status_label = tk.Label(win, text="Conflict remains", fg="red", font=("Arial", 10, "bold"))
        status_label.pack(pady=10)

        def is_unique(tag_v, desc_v, ignore_original=True):
            for t, d in self.tags.items():

                if not t or not d.get("description"):
                    continue

                if ignore_original:
                    if t == tag and d.get("description", "") == description:
                        continue

                if t == tag_v or d["description"] == desc_v:
                    return False

            return True

        def check_conflict():

            it = imported_tag_var.get().strip().upper()
            idesc = imported_desc_var.get().strip().upper()
            et = existing_tag_var.get().strip().upper()
            ed = existing_desc_var.get().strip().upper()

            imported_unique = is_unique(it, idesc, True)
            existing_unique = is_unique(et, ed, True)

            conflict = False

            if it and et and it != et:
                imported_tag_entry.config(bg="#ffcccc")
                existing_tag_entry.config(bg="#ffcccc")
                conflict = True
            else:
                imported_tag_entry.config(bg="#d4ffd4")
                existing_tag_entry.config(bg="#d4ffd4")

            if idesc and ed and idesc != ed:
                imported_desc_entry.config(bg="#ffcccc")
                existing_desc_entry.config(bg="#ffcccc")
                conflict = True
            else:
                imported_desc_entry.config(bg="#d4ffd4")
                existing_desc_entry.config(bg="#d4ffd4")

            if imported_unique and existing_unique:
                status_label.config(text="No conflict - both entries can be imported", fg="green")
                import_both_btn.config(state="normal")
                resolve_btn.config(state="disabled")
            elif not conflict:
                status_label.config(text="No conflict detected", fg="green")
                resolve_btn.config(state="normal")
                import_both_btn.config(state="disabled")
            else:
                status_label.config(text="Conflict remains", fg="red")
                resolve_btn.config(state="disabled")
                import_both_btn.config(state="disabled")

        def tag_arrow_to_existing():
            existing_tag_var.set(imported_tag_var.get())
            check_conflict()

        def tag_arrow_to_imported():
            imported_tag_var.set(existing_tag_var.get())
            check_conflict()

        def desc_arrow_to_existing():
            existing_desc_var.set(imported_desc_var.get())
            check_conflict()

        def desc_arrow_to_imported():
            imported_desc_var.set(existing_desc_var.get())
            check_conflict()

        tk.Label(left_frame, text="Tag", bg="#ffdddd").pack()
        imported_tag_entry = tk.Entry(left_frame, textvariable=imported_tag_var)
        imported_tag_entry.pack(fill="x", padx=10)

        tk.Label(left_frame, text="Description", bg="#ffdddd").pack()
        imported_desc_entry = tk.Entry(left_frame, textvariable=imported_desc_var)
        imported_desc_entry.pack(fill="x", padx=10)

        arrow_frame = tk.Frame(container)
        arrow_frame.pack(side="left", fill="y")

        tk.Button(arrow_frame, text="→", font=("Arial", 8), command=tag_arrow_to_existing).pack(pady=(25, 0))
        tk.Button(arrow_frame, text="←", font=("Arial", 8), command=tag_arrow_to_imported).pack(pady=0)

        tk.Button(arrow_frame, text="→", font=("Arial", 8), command=desc_arrow_to_existing).pack(pady=(10, 0))
        tk.Button(arrow_frame, text="←", font=("Arial", 8), command=desc_arrow_to_imported).pack(pady=0)

        tk.Label(right_frame, text="Tag", bg="#ffdddd").pack()
        existing_tag_entry = tk.Entry(right_frame, textvariable=existing_tag_var)
        existing_tag_entry.pack(fill="x", padx=10)

        tk.Label(right_frame, text="Description", bg="#ffdddd").pack()
        existing_desc_entry = tk.Entry(right_frame, textvariable=existing_desc_var)
        existing_desc_entry.pack(fill="x", padx=10)

        def resolve():

            result["action"] = "resolve"
            result["imported_tag"] = imported_tag_var.get().strip().upper()
            result["imported_description"] = imported_desc_var.get().strip().upper()
            result["existing_tag"] = existing_tag_var.get().strip().upper()
            result["existing_description"] = existing_desc_var.get().strip().upper()

            win.destroy()

        def import_both():

            result["action"] = "import_both"
            result["imported_tag"] = imported_tag_var.get().strip().upper()
            result["imported_description"] = imported_desc_var.get().strip().upper()
            result["existing_tag"] = existing_tag_var.get().strip().upper()
            result["existing_description"] = existing_desc_var.get().strip().upper()

            win.destroy()

        resolve_btn = tk.Button(win, text="Resolve Conflict", state="disabled", command=resolve)
        resolve_btn.pack(pady=5)

        import_both_btn = tk.Button(win, text="Import Both (No Conflict)", state="disabled", command=import_both)
        import_both_btn.pack(pady=5)

        for v in (imported_tag_var, imported_desc_var, existing_tag_var, existing_desc_var):
            v.trace_add("write", lambda *_: check_conflict())

        check_conflict()

        win.wait_window()
        return result

    def change_selected_tag(self):

        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0], "values")
        old_tag = item[0]

        new_tag = simpledialog.askstring("Change Tag", f"New tag for {old_tag}:")
        if not new_tag:
            return

        new_tag = new_tag.strip().upper()

        if new_tag in self.tags:
            messagebox.showerror("Error", "Tag already exists")
            return

        data = self.tags[old_tag]
        vessels = set(data["vessels"])

        self.tags[new_tag] = data
        del self.tags[old_tag]

        exports = []

        for v in vessels:
            exports.append({
                "old_tag": old_tag,
                "new_tag": new_tag,
                "row": data.get("row_data", {})
            })

        self.save_database()
        self.refresh_table()
        self.update_vessel_filter_list()
        self.write_exports({"GLOBAL": exports})

    def write_exports(self, exports):

        os.makedirs(EXPORT_FOLDER, exist_ok=True)

        all_files = []

        for vessel, changes in exports.items():

            rows = []

            for c in changes:

                row = dict(c["row"])
                row["old_tag"] = c["old_tag"]
                row["new_tag"] = c["new_tag"]
                rows.append(row)

            df = pd.DataFrame(rows)

            filename = f"{vessel}_BATCH_EXPORT.csv"
            path = os.path.join(EXPORT_FOLDER, filename)

            df.to_csv(path, index=False)

            all_files.append(path)

        messagebox.showinfo(
            "EXPORT REQUIRED",
            "Changes detected.\n\n"
            "ALL EXPORTS WRITTEN:\n" +
            "\n".join(all_files) +
            "\n\nTHESE FILES MUST BE RE-IMPORTED INTO THE SYSTEM.\n"
            f"LOCATION: {os.path.abspath(EXPORT_FOLDER)}"
        )


def main():

    root = tk.Tk()

    app = TagCentralApp(root)

    app.run = root.mainloop

    app.run()


if __name__ == "__main__":
    main()
