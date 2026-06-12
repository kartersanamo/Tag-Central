"""Documentation CLI commands."""

from __future__ import annotations

import argparse

from cli import output
from core.tag_central_app import TagCentralApp
from services.documentation_service import DOCUMENT_TYPES


def register(subparsers: argparse._SubParsersAction) -> None:
    docs_parser = subparsers.add_parser("docs", help="Documentation generation")
    docs_sub = docs_parser.add_subparsers(dest="docs_command", required=True)

    generate = docs_sub.add_parser("generate", help="Generate documentation package")
    generate.add_argument(
        "--types",
        default=",".join(DOCUMENT_TYPES.keys()),
        help="Comma-separated doc types",
    )
    generate.add_argument(
        "--formats",
        default="html",
        help="Comma-separated formats: html,excel,csv,word",
    )
    generate.add_argument("--vessel", default="ALL")
    generate.add_argument("--yes", action="store_true")
    generate.set_defaults(handler=_docs_generate)


def _docs_generate(args: argparse.Namespace, app: TagCentralApp) -> int:
    doc_types = [item.strip() for item in args.types.split(",") if item.strip()]
    formats = [item.strip() for item in args.formats.split(",") if item.strip()]
    if not args.yes:
        output.emit(
            {
                "dry_run": True,
                "types": doc_types,
                "formats": formats,
                "vessel": args.vessel,
                "message": "Re-run with --yes to generate.",
            },
            fmt=args.format,
            quiet=args.quiet,
        )
        return output.EXIT_OK
    result = app.docs_generate(doc_types=doc_types, formats=formats, vessel=args.vessel)
    output.emit(result, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK
