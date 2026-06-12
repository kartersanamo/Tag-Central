"""Tag CLI commands."""

from __future__ import annotations

import argparse

from cli import output
from core.tag_central_app import TagCentralApp
from services.find_replace_service import matches_find_scope


def register(subparsers: argparse._SubParsersAction) -> None:
    tags = subparsers.add_parser("tags", help="Tag list, show, diff, and mutations")
    tags_sub = tags.add_subparsers(dest="tags_command", required=True)

    list_parser = tags_sub.add_parser("list", help="List tags with optional filters")
    list_parser.add_argument("--vessel", default=None)
    list_parser.add_argument("--program", default=None)
    list_parser.add_argument("--search", default=None)
    list_parser.add_argument("--mismatches-only", action="store_true")
    list_parser.set_defaults(handler=_tags_list)

    show_parser = tags_sub.add_parser("show", help="Show one tag")
    show_parser.add_argument("tag")
    show_parser.set_defaults(handler=_tags_show)

    diff_parser = tags_sub.add_parser("diff", help="Proficy vs Cimplicity diff")
    diff_parser.add_argument("tag")
    diff_parser.set_defaults(handler=_tags_diff)

    add_parser = tags_sub.add_parser("add", help="Create a tag")
    add_parser.add_argument("--name", required=True)
    add_parser.add_argument("--description", required=True)
    add_parser.add_argument("--address", default="")
    add_parser.add_argument("--vessel", action="append", default=[])
    add_parser.add_argument(
        "--program", choices=["proficy", "cimplicity", "both"], default="both"
    )
    add_parser.add_argument("--no-queue", action="store_true")
    add_parser.set_defaults(handler=_tags_add)

    edit_parser = tags_sub.add_parser("edit", help="Edit a tag")
    edit_parser.add_argument("tag")
    edit_parser.add_argument("--name")
    edit_parser.add_argument("--description")
    edit_parser.add_argument("--address")
    edit_parser.add_argument("--vessel", action="append")
    edit_parser.set_defaults(handler=_tags_edit)

    delete_parser = tags_sub.add_parser("delete", help="Delete tag(s)")
    delete_parser.add_argument("tags", nargs="+")
    delete_parser.set_defaults(handler=_tags_delete)

    merge_parser = tags_sub.add_parser("merge", help="Merge two tags")
    merge_parser.add_argument("tag_a")
    merge_parser.add_argument("tag_b")
    merge_parser.add_argument("--survivor", required=True)
    merge_parser.set_defaults(handler=_tags_merge)

    align_parser = tags_sub.add_parser("align", help="Align tag(s) to Cimplicity")
    align_parser.add_argument("tags", nargs="+")
    align_parser.set_defaults(handler=_tags_align)

    increment_parser = tags_sub.add_parser(
        "increment", help="Number descriptions in mismatch group"
    )
    increment_parser.add_argument("tags", nargs="+")
    increment_parser.set_defaults(handler=_tags_increment)

    copy_parser = tags_sub.add_parser("copy", help="Copy tag rows as TSV")
    copy_parser.add_argument("tags", nargs="+")
    copy_parser.set_defaults(handler=_tags_copy)

    fr_parser = tags_sub.add_parser("find-replace", help="Find and replace tags")
    fr_parser.add_argument("--find", required=True)
    fr_parser.add_argument("--replace", default="")
    fr_parser.add_argument(
        "--scope",
        choices=["tag", "description", "both"],
        default="both",
    )
    fr_parser.add_argument("--apply", action="store_true")
    fr_parser.add_argument("--delete", action="store_true")
    fr_parser.add_argument("--yes", action="store_true")
    fr_parser.set_defaults(handler=_tags_find_replace)


def _tags_list(args: argparse.Namespace, app: TagCentralApp) -> int:
    rows = app.list_tags(
        vessel=args.vessel,
        program=args.program,
        search=args.search,
        mismatches_only=args.mismatches_only,
    )
    output.emit(rows, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tags_show(args: argparse.Namespace, app: TagCentralApp) -> int:
    output.emit(app.show_tag(args.tag), fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tags_diff(args: argparse.Namespace, app: TagCentralApp) -> int:
    output.emit(app.tag_diff(args.tag), fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tags_add(args: argparse.Namespace, app: TagCentralApp) -> int:
    vessels = set(args.vessel) if args.vessel else {"GLOBAL"}
    result = app.add_tag(
        tag_name=args.name,
        description=args.description,
        address=args.address,
        vessels=vessels,
        program=args.program,
        queue_proficy=not args.no_queue,
    )
    output.emit(result, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tags_edit(args: argparse.Namespace, app: TagCentralApp) -> int:
    vessels = set(args.vessel) if args.vessel else None
    result = app.edit_tag(
        args.tag,
        tag_name=args.name,
        description=args.description,
        address=args.address,
        vessels=vessels,
    )
    output.emit(result, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tags_delete(args: argparse.Namespace, app: TagCentralApp) -> int:
    count = app.delete_tags(args.tags)
    output.emit({"deleted": count}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tags_merge(args: argparse.Namespace, app: TagCentralApp) -> int:
    result = app.merge_tags(args.tag_a, args.tag_b, args.survivor)
    output.emit(result, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tags_align(args: argparse.Namespace, app: TagCentralApp) -> int:
    count = app.align_tags(args.tags)
    output.emit({"aligned": count}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tags_increment(args: argparse.Namespace, app: TagCentralApp) -> int:
    count = app.increment_descriptions(args.tags)
    output.emit({"updated": count}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tags_copy(args: argparse.Namespace, app: TagCentralApp) -> int:
    text = app.copy_tags(args.tags)
    if args.format == "json":
        output.emit({"tsv": text}, fmt="json", quiet=args.quiet)
    else:
        output.emit(text, fmt="table", quiet=args.quiet)
    return output.EXIT_OK


def _tags_find_replace(args: argparse.Namespace, app: TagCentralApp) -> int:
    if args.delete:
        if not args.yes:
            matching = [
                name
                for name, record in app.tags.items()
                if matches_find_scope(record, args.find, args.scope)
            ]
            output.emit(
                {
                    "dry_run": True,
                    "would_delete": len(matching),
                    "message": "Re-run with --delete --yes to apply.",
                },
                fmt=args.format,
                quiet=args.quiet,
            )
            return output.EXIT_OK
        count = app.find_replace_delete(args.find, args.scope)
        output.emit({"deleted": count}, fmt=args.format, quiet=args.quiet)
        return output.EXIT_OK

    if args.apply:
        if not args.yes:
            preview = app.find_replace_preview(args.find, args.replace, args.scope)
            preview["dry_run"] = True
            preview["message"] = "Re-run with --apply --yes to apply."
            output.emit(preview, fmt=args.format, quiet=args.quiet)
            return output.EXIT_OK
        count = app.find_replace_apply(args.find, args.replace, args.scope)
        output.emit({"updated": count}, fmt=args.format, quiet=args.quiet)
        return output.EXIT_OK

    preview = app.find_replace_preview(args.find, args.replace, args.scope)
    output.emit(preview, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK
