"""Documentation orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from controllers.controller_base import ControllerBase

import sys
from datetime import datetime
from pathlib import Path

from tkinter import messagebox

from app_identity import documentation_dir
from ui.documentation_dialog import DocumentationDialog
from ui.loading_dialog import LoadingDialog

if TYPE_CHECKING:
    from controllers.app_controller import AppController


class DocumentationController(ControllerBase):
    """Extracted from AppController — documentation_controller."""

    def generate_documentation(self) -> None:
        """Opens documentation wizard and writes a package next to the app."""
        vessels = sorted(
            {
                vessel
                for record in self._tags.values()
                for vessel in record.vessels
                if vessel.strip()
            }
        )
        options = DocumentationDialog(self._window.root, vessels).show()
        if options is None:
            return

        vessel = str(options.get("vessel", "ALL")).strip()
        vessel_filter = None if vessel.upper() == "ALL" else vessel
        doc_types = list(options.get("doc_types", []))

        loading = LoadingDialog(self._window.root, title="Generating Documentation...")
        loading.show("Building documentation tables...")
        try:
            tables = self._documentation.build_tables(
                self._tags,
                selected_types=doc_types,
                vessel_filter=vessel_filter,
                pending_exports=self._export_queue.all_entries(),
            )
            if not tables:
                messagebox.showinfo(
                    "No Documentation",
                    "No tables were generated for the selected options.",
                    parent=self._window.root,
                )
                return

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = documentation_dir() / f"TagCentral_{timestamp}"
            loading.update_status("Writing export files...")
            result = self._documentation.write_package(
                tables,
                output_dir,
                write_html=bool(options.get("html")),
                write_excel=bool(options.get("excel")),
                write_csv=bool(options.get("csv")),
                write_word=bool(options.get("word")),
                vessel_filter=vessel,
                tag_count=len(self._tags),
            )
        except Exception as error:
            messagebox.showerror(
                "Documentation Failed",
                f"Could not generate documentation.\n\n{error}",
                parent=self._window.root,
            )
            return
        finally:
            loading.close()

        index_file = output_dir / "index.html"
        lines = [
            f"Generated {len(tables)} document section(s).",
            f"Output folder:\n{output_dir}",
        ]
        if bool(options.get("html")) and index_file.exists():
            lines.append(f"\nOpen in browser:\n{index_file}")
        if bool(options.get("word")) and not any(
            path.suffix == ".docx" for path in result.written_files
        ):
            lines.append(
                "\nWord export was skipped (install python-docx for .docx support)."
            )
        messagebox.showinfo(
            "Documentation Generated",
            "\n".join(lines),
            parent=self._window.root,
        )
        self._reveal_path(output_dir)


    def _reveal_path(self, path: Path) -> None:
        """Opens a folder in Finder / Explorer."""
        try:
            target = path.resolve()
            if sys.platform == "darwin":
                import subprocess

                subprocess.run(["open", str(target)], check=False)
            elif sys.platform == "win32":
                import os

                os.startfile(target)  # type: ignore[attr-defined]
        except OSError:
            pass

