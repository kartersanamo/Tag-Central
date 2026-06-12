"""Tag Central CLI entry point."""

from __future__ import annotations

import argparse
import sys

from app_identity import APP_NAME, ensure_user_data_layout, is_frozen

from cli import output
from cli.commands import backup_cmd, cimplicity_cmd, docs_cmd, export_cmd, import_cmd, tags
from core.exceptions import PolicyAbortError, TagCentralError
from core.tag_central_app import TagCentralApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=APP_NAME, description=f"{APP_NAME} CLI")
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format for list/show commands",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout output")

    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Application status summary")
    status_parser.set_defaults(handler=_status)

    tags.register(subparsers)
    import_cmd.register(subparsers)
    export_cmd.register(subparsers)
    backup_cmd.register(subparsers)
    docs_cmd.register(subparsers)
    cimplicity_cmd.register(subparsers)

    return parser


def _status(args: argparse.Namespace, app: TagCentralApp) -> int:
    output.emit(app.status(), fmt=args.format, quiet=args.quiet)
    return output.EXIT_OK


def run_cli(argv: list[str] | None = None) -> int:
    """Runs CLI and returns exit code."""
    if is_frozen():
        ensure_user_data_layout()

    parser = build_parser()
    args = parser.parse_args(argv)

    app = TagCentralApp()
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return output.EXIT_ERROR

    try:
        return handler(args, app)
    except PolicyAbortError as error:
        output.emit_error(str(error))
        return output.EXIT_POLICY
    except TagCentralError as error:
        output.emit_error(str(error))
        return output.EXIT_ERROR
    except ValueError as error:
        output.emit_error(str(error))
        return output.EXIT_ERROR
    except KeyboardInterrupt:
        output.emit_error("Interrupted.")
        return output.EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(run_cli())
