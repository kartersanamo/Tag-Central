"""Cimplicity review and tasks CLI commands."""

from __future__ import annotations

import argparse

from cli import output
from core.tag_central_app import TagCentralApp


def register(subparsers: argparse._SubParsersAction) -> None:
    cim_parser = subparsers.add_parser("cimplicity", help="Cimplicity review and tasks")
    cim_sub = cim_parser.add_subparsers(dest="cimplicity_command", required=True)

    review_parser = cim_sub.add_parser("review", help="Review queue")
    review_sub = review_parser.add_subparsers(dest="review_command", required=True)

    review_sub.add_parser("list", help="List review queue").set_defaults(
        handler=_review_list
    )

    create_parser = review_sub.add_parser(
        "create-proficy", help="Create Proficy tags from review items"
    )
    create_parser.add_argument("--all", action="store_true")
    create_parser.add_argument("--vessel", action="append")
    create_parser.add_argument("--pt-id", action="append")
    create_parser.add_argument("--yes", action="store_true")
    create_parser.set_defaults(handler=_review_create)

    dismiss_parser = review_sub.add_parser("dismiss", help="Dismiss review items")
    dismiss_parser.add_argument("--all", action="store_true")
    dismiss_parser.add_argument("--vessel", action="append")
    dismiss_parser.add_argument("--pt-id", action="append")
    dismiss_parser.add_argument("--yes", action="store_true")
    dismiss_parser.set_defaults(handler=_review_dismiss)

    tasks_parser = cim_sub.add_parser("tasks", help="Manual Cimplicity tasks")
    tasks_sub = tasks_parser.add_subparsers(dest="tasks_command", required=True)

    tasks_sub.add_parser("list", help="List manual tasks").set_defaults(
        handler=_tasks_list
    )

    toggle_parser = tasks_sub.add_parser("toggle", help="Toggle task done state")
    toggle_parser.add_argument("task_id")
    toggle_parser.add_argument("--done", action="store_true")
    toggle_parser.add_argument("--pending", action="store_true")
    toggle_parser.set_defaults(handler=_tasks_toggle)

    clear_parser = tasks_sub.add_parser("clear-done", help="Remove completed tasks")
    clear_parser.add_argument("--yes", action="store_true")
    clear_parser.set_defaults(handler=_tasks_clear_done)


def _pair_items(args: argparse.Namespace) -> list[tuple[str, str]] | None:
    vessels = args.vessel or []
    pt_ids = getattr(args, "pt_id", None) or []
    if vessels and pt_ids and len(vessels) == len(pt_ids):
        return list(zip(vessels, pt_ids))
    if vessels or pt_ids:
        raise ValueError("Provide matching --vessel and --pt-id pairs.")
    return None


def _review_list(args: argparse.Namespace, app: TagCentralApp) -> int:
    output.emit(app.cimplicity_review_list(), fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _review_create(args: argparse.Namespace, app: TagCentralApp) -> int:
    if not args.yes:
        count = len(app.cimplicity_review_list()) if args.all else 0
        output.emit(
            {
                "dry_run": True,
                "items": count or "selected",
                "message": "Re-run with --yes to create Proficy tags.",
            },
            fmt=args.format,
            quiet=args.quiet,
        )
        return output.EXIT_OK
    items = None if args.all else _pair_items(args)
    result = app.cimplicity_review_create_proficy(items, all_items=args.all)
    output.emit(result, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _review_dismiss(args: argparse.Namespace, app: TagCentralApp) -> int:
    if not args.yes:
        output.emit(
            {"dry_run": True, "message": "Re-run with --yes to dismiss."},
            fmt=args.format,
            quiet=args.quiet,
        )
        return output.EXIT_OK
    items = None if args.all else _pair_items(args)
    removed = app.cimplicity_review_dismiss(items, all_items=args.all)
    output.emit({"dismissed": removed}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tasks_list(args: argparse.Namespace, app: TagCentralApp) -> int:
    output.emit(app.cimplicity_tasks_list(), fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tasks_toggle(args: argparse.Namespace, app: TagCentralApp) -> int:
    done = True if args.done else False if args.pending else True
    app.cimplicity_tasks_toggle(args.task_id, done=done)
    output.emit({"task_id": args.task_id, "done": done}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def _tasks_clear_done(args: argparse.Namespace, app: TagCentralApp) -> int:
    if not args.yes:
        output.emit(
            {"dry_run": True, "message": "Re-run with --yes to clear done tasks."},
            fmt=args.format,
            quiet=args.quiet,
        )
        return output.EXIT_OK
    cleared = app.cimplicity_tasks_clear_done()
    output.emit({"cleared": cleared}, fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK
