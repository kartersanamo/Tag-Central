"""Dialog to configure and generate engineering documentation packages."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from services.documentation_service import DOCUMENT_TYPES


class DocumentationDialog:
    """Collects documentation types, formats, and vessel scope."""

    def __init__(
        self,
        parent: tk.Tk,
        vessels: list[str],
    ) -> None:
        self._result: dict[str, object] | None = None
        self._window = tk.Toplevel(parent)
        self._window.title("Generate Documentation")
        self._window.geometry("720x640")
        self._window.transient(parent)
        self._window.grab_set()

        self._doc_vars: dict[str, tk.BooleanVar] = {}
        self._html_var = tk.BooleanVar(value=True)
        self._excel_var = tk.BooleanVar(value=True)
        self._csv_var = tk.BooleanVar(value=True)
        self._word_var = tk.BooleanVar(value=False)
        self._vessel_var = tk.StringVar(value="ALL")

        self._build_ui(vessels)
        self._window.protocol("WM_DELETE_WINDOW", self._cancel)

    def _build_ui(self, vessels: list[str]) -> None:
        header = ttk.Frame(self._window, padding=14)
        header.pack(fill="x")
        ttk.Label(
            header,
            text="Auto Documentation",
            font=("Helvetica", 14, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            header,
            text=(
                "Build IO lists, alarm lists, tag dictionaries, commissioning checklists, "
                "and more from your current tag database. Output is written next to the app "
                "under Documentation/."
            ),
            wraplength=680,
        ).pack(anchor="w", pady=(6, 0))

        scope = ttk.LabelFrame(self._window, text="Scope", padding=12)
        scope.pack(fill="x", padx=14, pady=(0, 10))
        ttk.Label(scope, text="Vessel").pack(side="left", padx=(0, 8))
        ttk.Combobox(
            scope,
            textvariable=self._vessel_var,
            values=["ALL", *vessels],
            state="readonly",
            width=28,
        ).pack(side="left")

        docs = ttk.LabelFrame(self._window, text="Documents to generate", padding=12)
        docs.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        canvas = tk.Canvas(docs, highlightthickness=0, height=220)
        scroll = ttk.Scrollbar(docs, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind(
            "<Configure>",
            lambda _event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        for doc_id, (title, description) in DOCUMENT_TYPES.items():
            var = tk.BooleanVar(value=True)
            self._doc_vars[doc_id] = var
            row = ttk.Frame(inner)
            row.pack(fill="x", pady=4)
            ttk.Checkbutton(row, text=title, variable=var).pack(anchor="w")
            ttk.Label(row, text=description, foreground="#4b5563", wraplength=620).pack(
                anchor="w", padx=(22, 0)
            )

        formats = ttk.LabelFrame(self._window, text="Export formats", padding=12)
        formats.pack(fill="x", padx=14, pady=(0, 10))
        ttk.Checkbutton(
            formats,
            text="HTML dashboard (visual — open index.html in a browser; Print → PDF)",
            variable=self._html_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            formats,
            text="Excel workbook (one sheet per document)",
            variable=self._excel_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            formats,
            text="CSV pack (one file per document)",
            variable=self._csv_var,
        ).pack(anchor="w")
        ttk.Checkbutton(
            formats,
            text="Word document (.docx — requires python-docx)",
            variable=self._word_var,
        ).pack(anchor="w")

        buttons = ttk.Frame(self._window, padding=(14, 0, 14, 14))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Generate", command=self._generate).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side="right")

    def _generate(self) -> None:
        selected = [doc_id for doc_id, var in self._doc_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning(
                "No Documents",
                "Select at least one document type.",
                parent=self._window,
            )
            return
        if not any(
            (
                self._html_var.get(),
                self._excel_var.get(),
                self._csv_var.get(),
                self._word_var.get(),
            )
        ):
            messagebox.showwarning(
                "No Format",
                "Select at least one export format.",
                parent=self._window,
            )
            return
        self._result = {
            "doc_types": selected,
            "vessel": self._vessel_var.get().strip(),
            "html": self._html_var.get(),
            "excel": self._excel_var.get(),
            "csv": self._csv_var.get(),
            "word": self._word_var.get(),
        }
        self._window.destroy()

    def _cancel(self) -> None:
        self._result = None
        self._window.destroy()

    def show(self) -> dict[str, object] | None:
        self._window.wait_window()
        return self._result
