"""Backup CLI commands."""

from __future__ import annotations

import argparse

from cli import output
from core.tag_central_app import TagCentralApp


def register(subparsers: argparse._SubParsersAction) -> None:
    backup_parser = subparsers.add_parser("backup", help="Backup management")
    backup_sub = backup_parser.add_subparsers(dest="backup_command", required=True)

    backup_sub.add_parser("list", help="List backups").set_defaults(handler=_backup_list)

    create_parser = backup_sub.add_parser("create", help="Create backup snapshot")
    create_parser.add_argument("--prefix", default="backup")
    create_parser.set_defaults(handler=_backup_create)

    restore_parser = backup_sub.add_parser("restore", help="Restore named backup")
    restore_parser.add_argument("name")
    restore_parser.add_argument("--yes", action="store_true")
    restore_parser.set_defaults(handler=_backup_restore)

    delete_parser = backup_sub.add_parser("delete", help="Delete named backup")
    delete_parser.add_argument("name")
    delete_parser.add_argument("--yes", action="store_true")
    delete_parser.set_defaults(handler=_backup_delete)

    revert_parser = backup_sub.add_parser("revert", help="Revert preload backup")
    revert_parser.add_argument("--yes", action="store_true")
    revert_parser.set_defaults(handler=_backup_revert)


def _backup_list(args: argparse.Namespace, app: TagCentralApp) -> int:
    output.emit(app.backup_list(), fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _backup_create(args: argparse.Namespace, app: TagCentralApp) -> int:
    path = app.backup_create(prefix=args.prefix)
    output.emit({"path": path}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _backup_restore(args: argparse.Namespace, app: TagCentralApp) -> int:
    if not args.yes:
        output.emit(
            {
                "dry_run": True,
                "backup": args.name,
                "message": "Re-run with --yes to restore.",
            },
            fmt=args.format,
            quiet=args.quiet,
        )
        return output.EXIT_OK
    app.backup_restore(args.name)
    output.emit({"restored": args.name}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _backup_delete(args: argparse.Namespace, app: TagCentralApp) -> int:
    if not args.yes:
        output.emit(
            {
                "dry_run": True,
                "backup": args.name,
                "message": "Re-run with --yes to delete.",
            },
            fmt=args.format,
            quiet=args.quiet,
        )
        return output.EXIT_OK
    app.backup_delete(args.name)
    output.emit({"deleted": args.name}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _backup_revert(args: argparse.Namespace, app: TagCentralApp) -> int:
    if not args.yes:
        output.emit(
            {"dry_run": True, "message": "Re-run with --yes to revert preload backup."},
            fmt=args.format,
            quiet=args.quiet,
        )
        return output.EXIT_OK
    app.backup_revert()
    output.emit({"reverted": True}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK
