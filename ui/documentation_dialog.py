"""Dialog to configure and generate engineering documentation packages."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from services.documentation_service import DOCUMENT_TYPES
from ui.ctk_theme import FONT_BODY, TEXT_MUTED, button_accent_kwargs, button_neutral_kwargs


class DocumentationDialog:
    """Collects documentation types, formats, and vessel scope."""

    def __init__(
        self,
        parent: ctk.CTk,
        vessels: list[str],
    ) -> None:
        self._result: dict[str, object] | None = None
        self._window = ctk.CTkToplevel(parent)
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
        header = ctk.CTkFrame(self._window, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(
            header,
            text="Auto Documentation",
            font=(FONT_BODY[0], 16, "bold"),
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text=(
                "Build IO lists, alarm lists, tag dictionaries, commissioning checklists, "
                "and more from your current tag database. Output is written next to the app "
                "under Documentation/."
            ),
            font=FONT_BODY,
            wraplength=680,
            justify="left",
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

        scope = ctk.CTkFrame(self._window)
        scope.pack(fill="x", padx=14, pady=(0, 10))
        scope_inner = ctk.CTkFrame(scope, fg_color="transparent")
        scope_inner.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(scope_inner, text="Scope", font=(FONT_BODY[0], FONT_BODY[1], "bold")).pack(
            anchor="w", pady=(0, 8)
        )
        row = ctk.CTkFrame(scope_inner, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkLabel(row, text="Vessel", font=FONT_BODY).pack(side="left", padx=(0, 8))
        ctk.CTkComboBox(
            row,
            textvariable=self._vessel_var,
            values=["ALL", *vessels],
            state="readonly",
            width=220,
        ).pack(side="left")

        docs = ctk.CTkFrame(self._window)
        docs.pack(fill="both", expand=True, padx=14, pady=(0, 10))
        ctk.CTkLabel(
            docs,
            text="Documents to generate",
            font=(FONT_BODY[0], FONT_BODY[1], "bold"),
            anchor="w",
        ).pack(anchor="w", padx=12, pady=(12, 6))
        scroll = ctk.CTkScrollableFrame(docs, height=220)
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        for doc_id, (title, description) in DOCUMENT_TYPES.items():
            var = tk.BooleanVar(value=True)
            self._doc_vars[doc_id] = var
            doc_row = ctk.CTkFrame(scroll, fg_color="transparent")
            doc_row.pack(fill="x", pady=4)
            ctk.CTkCheckBox(doc_row, text=title, variable=var, font=FONT_BODY).pack(
                anchor="w"
            )
            ctk.CTkLabel(
                doc_row,
                text=description,
                font=FONT_BODY,
                text_color=TEXT_MUTED,
                wraplength=620,
                justify="left",
                anchor="w",
            ).pack(anchor="w", padx=(26, 0))

        formats = ctk.CTkFrame(self._window)
        formats.pack(fill="x", padx=14, pady=(0, 10))
        formats_inner = ctk.CTkFrame(formats, fg_color="transparent")
        formats_inner.pack(fill="x", padx=12, pady=12)
        ctk.CTkLabel(
            formats_inner,
            text="Export formats",
            font=(FONT_BODY[0], FONT_BODY[1], "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkCheckBox(
            formats_inner,
            text="HTML dashboard (visual — open index.html in a browser; Print → PDF)",
            variable=self._html_var,
            font=FONT_BODY,
        ).pack(anchor="w")
        ctk.CTkCheckBox(
            formats_inner,
            text="Excel workbook (one sheet per document)",
            variable=self._excel_var,
            font=FONT_BODY,
        ).pack(anchor="w")
        ctk.CTkCheckBox(
            formats_inner,
            text="CSV pack (one file per document)",
            variable=self._csv_var,
            font=FONT_BODY,
        ).pack(anchor="w")
        ctk.CTkCheckBox(
            formats_inner,
            text="Word document (.docx — requires python-docx)",
            variable=self._word_var,
            font=FONT_BODY,
        ).pack(anchor="w")

        buttons = ctk.CTkFrame(self._window, fg_color="transparent")
        buttons.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(
            buttons, text="Generate", command=self._generate, **button_accent_kwargs()
        ).pack(side="left")
        ctk.CTkButton(
            buttons, text="Cancel", command=self._cancel, **button_neutral_kwargs()
        ).pack(side="right")

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
