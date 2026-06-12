"""Import CLI commands."""

from __future__ import annotations

import argparse

from cli import output
from core.import_options import ImportOptions
from core.tag_central_app import TagCentralApp


def register(subparsers: argparse._SubParsersAction) -> None:
    import_parser = subparsers.add_parser("import", help="Import Proficy or Cimplicity files")
    import_sub = import_parser.add_subparsers(dest="import_command", required=True)

    proficy = import_sub.add_parser("proficy", help="Import Proficy spreadsheet")
    proficy.add_argument("--file", required=True)
    proficy.add_argument("--vessel", required=True)
    proficy.add_argument("--yes", action="store_true")
    proficy.add_argument(
        "--conflict-action",
        choices=["skip", "use_imported", "use_existing", "keep_both"],
        default="skip",
    )
    proficy.add_argument(
        "--descriptions",
        choices=["auto", "fail"],
        default="auto",
    )
    proficy.set_defaults(handler=_import_proficy)

    cimplicity = import_sub.add_parser("cimplicity", help="Import Cimplicity CSV")
    cimplicity.add_argument("--file", required=True)
    cimplicity.add_argument("--vessel", required=True)
    cimplicity.add_argument("--yes", action="store_true")
    cimplicity.add_argument(
        "--sync-action",
        choices=["align_proficy", "link_only", "flag_manual_cimplicity", "skip"],
        default="skip",
    )
    cimplicity.add_argument(
        "--ambiguous-action",
        choices=[
            "align_selected",
            "merge_then_align",
            "link_only_selected",
            "flag_manual_cimplicity",
            "skip",
        ],
        default="skip",
    )
    cimplicity.add_argument(
        "--descriptions",
        choices=["auto", "fail"],
        default="auto",
    )
    cimplicity.set_defaults(handler=_import_cimplicity)


def _import_options(args: argparse.Namespace) -> ImportOptions:
    return ImportOptions(
        yes=bool(getattr(args, "yes", False)),
        conflict_action=getattr(args, "conflict_action", "skip"),
        sync_action=getattr(args, "sync_action", "skip"),
        ambiguous_action=getattr(args, "ambiguous_action", "skip"),
        descriptions=getattr(args, "descriptions", "auto"),
    )


def _import_proficy(args: argparse.Namespace, app: TagCentralApp) -> int:
    result = app.import_proficy(args.file, args.vessel, _import_options(args))
    output.emit(result, fmt=args.format, quiet=args.quiet)
    if result.get("dry_run"):
        if args.format != "json" and not args.quiet:
            print(result.get("message", ""))
        return output.EXIT_OK
    return output.EXIT_OK


def _import_cimplicity(args: argparse.Namespace, app: TagCentralApp) -> int:
    result = app.import_cimplicity(args.file, args.vessel, _import_options(args))
    output.emit(result, fmt=args.format, quiet=args.quiet)
    if result.get("dry_run"):
        if args.format != "json" and not args.quiet:
            print(result.get("message", ""))
        return output.EXIT_OK
    return output.EXIT_OK
