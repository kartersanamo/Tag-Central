"""Base class exposing AppContext state with legacy attribute names."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from controllers.app_context import AppContext
    from controllers.app_controller import AppController


class ControllerBase:
    """Maps self._foo attributes to AppContext for extracted controller methods."""

    def __init__(self, ctx: AppContext, app: AppController) -> None:
        self._ctx = ctx
        self._app = app

    @property
    def _repository(self):
        return self._ctx.repository

    @property
    def _loader(self):
        return self._ctx.loader

    @property
    def _cimplicity_loader(self):
        return self._ctx.cimplicity_loader

    @property
    def _suggester(self):
        return self._ctx.suggester

    @property
    def _export_service(self):
        return self._ctx.export_service

    @property
    def _backup_service(self):
        return self._ctx.backup_service

    @property
    def _sync(self):
        return self._ctx.sync

    @property
    def _cross_program(self):
        return self._ctx.cross_program

    @property
    def _cimplicity_report(self):
        return self._ctx.cimplicity_report

    @property
    def _manual_tasks(self):
        return self._ctx.manual_tasks

    @property
    def _cimplicity_manual_entries(self):
        return self._ctx.cimplicity_manual_entries

    @_cimplicity_manual_entries.setter
    def _cimplicity_manual_entries(self, value):
        self._ctx.cimplicity_manual_entries = value

    @property
    def _tags(self):
        return self._ctx.tags

    @_tags.setter
    def _tags(self, value):
        self._ctx.tags = value

    @property
    def _active_vessel_filter(self):
        return self._ctx.active_vessel_filter

    @_active_vessel_filter.setter
    def _active_vessel_filter(self, value):
        self._ctx.active_vessel_filter = value

    @property
    def _conflicted_tags(self):
        return self._ctx.conflicted_tags

    @_conflicted_tags.setter
    def _conflicted_tags(self, value):
        self._ctx.conflicted_tags = value

    @property
    def _tag_conflict_peers(self):
        return self._ctx.tag_conflict_peers

    @_tag_conflict_peers.setter
    def _tag_conflict_peers(self, value):
        self._ctx.tag_conflict_peers = value

    @property
    def _tag_mismatch_group_label(self):
        return self._ctx.tag_mismatch_group_label

    @_tag_mismatch_group_label.setter
    def _tag_mismatch_group_label(self, value):
        self._ctx.tag_mismatch_group_label = value

    @property
    def _tag_mismatch_type(self):
        return self._ctx.tag_mismatch_type

    @_tag_mismatch_type.setter
    def _tag_mismatch_type(self, value):
        self._ctx.tag_mismatch_type = value

    @property
    def _export_queue(self):
        return self._ctx.export_queue

    @property
    def _export_validator(self):
        return self._ctx.export_validator

    @property
    def _mismatch_service(self):
        return self._ctx.mismatch_service

    @property
    def _proficy_analyzer(self):
        return self._ctx.proficy_analyzer

    @property
    def _merge_service(self):
        return self._ctx.merge_service

    @property
    def _documentation(self):
        return self._ctx.documentation

    @property
    def _ui_worker(self):
        return self._ctx.ui_worker

    @property
    def _persist_after_id(self):
        return self._ctx.persist_after_id

    @_persist_after_id.setter
    def _persist_after_id(self, value):
        self._ctx.persist_after_id = value

    @property
    def _refresh_generation(self):
        return self._ctx.refresh_generation

    @_refresh_generation.setter
    def _refresh_generation(self, value):
        self._ctx.refresh_generation = value

    @property
    def _last_cimplicity_link_report(self):
        return self._ctx.last_cimplicity_link_report

    @_last_cimplicity_link_report.setter
    def _last_cimplicity_link_report(self, value):
        self._ctx.last_cimplicity_link_report = value

    @property
    def _sort_column(self):
        return self._ctx.sort_column

    @_sort_column.setter
    def _sort_column(self, value):
        self._ctx.sort_column = value

    @property
    def _sort_descending(self):
        return self._ctx.sort_descending

    @_sort_descending.setter
    def _sort_descending(self, value):
        self._ctx.sort_descending = value

    @property
    def _sort_before_internal_mismatches(self):
        return self._ctx.sort_before_internal_mismatches

    @_sort_before_internal_mismatches.setter
    def _sort_before_internal_mismatches(self, value):
        self._ctx.sort_before_internal_mismatches = value

    @property
    def _array_children_by_base(self):
        return self._ctx.array_children_by_base

    @_array_children_by_base.setter
    def _array_children_by_base(self, value):
        self._ctx.array_children_by_base = value

    @property
    def _expanded_array_bases(self):
        return self._ctx.expanded_array_bases

    @_expanded_array_bases.setter
    def _expanded_array_bases(self, value):
        self._ctx.expanded_array_bases = value

    @property
    def _column_heading_labels(self):
        return self._ctx.column_heading_labels

    @property
    def _window(self):
        return self._ctx.window
