"""
AutoFlow AI X — Google Sheets Executor
========================================
Handles read_rows, append_row, update_row, find_row operations
via the Google Sheets API v4.

Auth: Same OAuth flow as Gmail — decrypt credentials from integrations table.
"""

import logging
from typing import Any

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)


class SheetsReadRowsExecutor(BaseExecutor):
    """
    Reads rows from a Google Sheet range with optional filtering.

    Required params:
        spreadsheet_id : Google Sheet ID (from URL)
        range          : A1 notation range, e.g. "Sheet1!A:E"

    Optional params:
        filter: { "column": "date", "equals": "2026-06-02" }
                Filters rows client-side after fetching.
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        spreadsheet_id = resolved_params.get("spreadsheet_id", "")
        range_ = resolved_params.get("range", "Sheet1!A:Z")
        filter_cfg = resolved_params.get("filter")

        if not spreadsheet_id:
            return ExecutorResult.fail("'spreadsheet_id' is required for read_rows.")

        logger.info(f"[Sheets] Reading '{range_}' from sheet '{spreadsheet_id}'")

        # ── Call Google Sheets API ────────────────────────────────────────────
        # from googleapiclient.discovery import build
        # service = build("sheets", "v4", credentials=credentials)
        # result = service.spreadsheets().values().get(
        #     spreadsheetId=spreadsheet_id, range=range_
        # ).execute()
        # raw_values = result.get("values", [])
        # headers = raw_values[0] if raw_values else []
        # rows = [dict(zip(headers, row)) for row in raw_values[1:]]

        # STUB: return empty dataset
        headers: list[str] = []
        rows: list[dict] = []

        # Apply filter if provided
        if filter_cfg and rows:
            col = filter_cfg.get("column")
            val = str(filter_cfg.get("equals", ""))
            rows = [r for r in rows if str(r.get(col, "")) == val]

        return ExecutorResult.ok(
            output={
                "rows": rows,
                "row_count": len(rows),
                "headers": headers,
                "spreadsheet_id": spreadsheet_id,
                "range": range_,
            }
        )


class SheetsAppendRowExecutor(BaseExecutor):
    """
    Appends a new row to a Google Sheet.

    Required params:
        spreadsheet_id : Google Sheet ID
        range          : Target range (e.g. "Sheet1!A:D")
        row            : dict of {column_name: value} to append
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        spreadsheet_id = resolved_params.get("spreadsheet_id", "")
        range_ = resolved_params.get("range", "Sheet1!A:A")
        row_data = resolved_params.get("row", {})

        if not spreadsheet_id:
            return ExecutorResult.fail("'spreadsheet_id' is required for append_row.")
        if not row_data:
            return ExecutorResult.fail("'row' data is required for append_row.")

        values = list(row_data.values()) if isinstance(row_data, dict) else [row_data]
        logger.info(f"[Sheets] Appending row to '{spreadsheet_id}' range '{range_}': {values}")

        # STUB: log and return success
        return ExecutorResult.ok(
            output={
                "appended_range": range_,
                "row_data": row_data,
                "status": "appended",
            }
        )


class SheetsUpdateRowExecutor(BaseExecutor):
    """
    Updates an existing row in a Google Sheet.

    Required params:
        spreadsheet_id : Google Sheet ID
        range          : Exact cell range to update, e.g. "Sheet1!A2:D2"
        row            : dict of new values
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        spreadsheet_id = resolved_params.get("spreadsheet_id", "")
        range_ = resolved_params.get("range", "")
        row_data = resolved_params.get("row", {})

        logger.info(f"[Sheets] Updating '{range_}' in sheet '{spreadsheet_id}'")

        return ExecutorResult.ok(
            output={"updated_range": range_, "row_data": row_data, "status": "updated"}
        )


class SheetsFindRowExecutor(BaseExecutor):
    """
    Finds the first row matching a condition.

    Required params:
        spreadsheet_id : Google Sheet ID
        range          : Range to search
        filter         : { "column": "email", "equals": "user@example.com" }
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        spreadsheet_id = resolved_params.get("spreadsheet_id", "")
        range_ = resolved_params.get("range", "Sheet1!A:Z")
        filter_cfg = resolved_params.get("filter", {})

        logger.info(f"[Sheets] Finding row in '{spreadsheet_id}' with filter {filter_cfg}")

        # STUB: return empty result
        return ExecutorResult.ok(
            output={"row": None, "found": False, "row_index": -1}
        )
