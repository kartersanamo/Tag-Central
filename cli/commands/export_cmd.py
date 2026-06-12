"""Export CLI commands."""

from __future__ import annotations

import argparse

from cli import output
from core.tag_central_app import TagCentralApp


def register(subparsers: argparse._SubParsersAction) -> None:
    export_parser = subparsers.add_parser("export", help="Export queue and batch export")
    export_sub = export_parser.add_subparsers(dest="export_command", required=True)

    run_parser = export_sub.add_parser("run", help="Write pending export batches")
    run_parser.add_argument("--validate", action="store_true")
    run_parser.add_argument("--yes", action="store_true")
    run_parser.set_defaults(handler=_export_run)

    queue_parser = export_sub.add_parser("queue", help="Inspect export queue")
    queue_sub = queue_parser.add_subparsers(dest="queue_command", required=True)

    queue_list = queue_sub.add_parser("list", help="List queued export rows")
    queue_list.set_defaults(handler=_export_queue_list)

    queue_remove = queue_sub.add_parser("remove", help="Remove queued row by ID")
    queue_remove.add_argument("change_id")
    queue_remove.set_defaults(handler=_export_queue_remove)

    queue_edit = queue_sub.add_parser("edit", help="Edit queued row fields")
    queue_edit.add_argument("change_id")
    queue_edit.add_argument("--name")
    queue_edit.add_argument("--description")
    queue_edit.add_argument("--address")
    queue_edit.set_defaults(handler=_export_queue_edit)

    validate_parser = export_sub.add_parser("validate", help="Validate export CSV")
    validate_parser.add_argument("--file", required=True)
    validate_parser.add_argument("--vessel", required=True)
    validate_parser.set_defaults(handler=_export_validate)


def _export_run(args: argparse.Namespace, app: TagCentralApp) -> int:
    if app.export_queue.count() == 0:
        output.emit_error("No pending changes to export.")
        return output.EXIT_ERROR
    if not args.yes:
        output.emit(
            {
                "dry_run": True,
                "pending": app.export_queue.count(),
                "vessels": app.export_queue.vessel_count(),
                "message": "Re-run with --yes to export.",
            },
            fmt=args.format,
            quiet=args.quiet,
        )
        return output.EXIT_OK
    result = app.export_run(validate=args.validate)
    output.emit(result, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _export_queue_list(args: argparse.Namespace, app: TagCentralApp) -> int:
    output.emit(app.export_queue_list(), fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _export_queue_remove(args: argparse.Namespace, app: TagCentralApp) -> int:
    app.export_queue_remove(args.change_id)
    output.emit({"removed": args.change_id}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _export_queue_edit(args: argparse.Namespace, app: TagCentralApp) -> int:
    result = app.export_queue_edit(
        args.change_id,
        name=args.name,
        description=args.description,
        address=args.address,
    )
    output.emit(result, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _export_validate(args: argparse.Namespace, app: TagCentralApp) -> int:
    result = app.export_validate(args.file, args.vessel)
    output.emit(result, fmt=args.format, quiet=args.quiet)
    return output.EXIT_ERROR if not result.get("ok") else output.EXIT_OK
