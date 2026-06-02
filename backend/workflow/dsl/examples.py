"""
AutoFlow AI X — Canonical DSL Examples
========================================
These are the ground-truth reference examples used in the Groq system prompt
and in the template gallery. Defining them in Python (not raw JSON) means they
are always validated by Pydantic before being used anywhere.
"""

from backend.workflow.dsl.schema import (
    ManualTriggerConfig,
    NodeType,
    OperationType,
    RetryPolicy,
    ScheduleTriggerConfig,
    ServiceType,
    TriggerConfig,
    TriggerType,
    WorkflowDSL,
    WorkflowEdgeDSL,
    WorkflowNodeDSL,
)

# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLE A: Appointment Reminder Workflow (Healthcare)
# Trigger: Every day at 9 AM UTC
# Flow: Read appointments from Google Sheets → for each patient → send email
# ─────────────────────────────────────────────────────────────────────────────

APPOINTMENT_REMINDER_DSL = WorkflowDSL(
    id="example-appointment-reminder",
    name="Daily Appointment Reminders",
    description=(
        "Every morning at 9 AM, reads today's appointments from Google Sheets "
        "and sends a reminder email to each patient."
    ),
    industry="healthcare",
    version=1,
    tags=["reminders", "email", "healthcare", "google_sheets"],
    trigger=TriggerConfig(
        type=TriggerType.schedule,
        config=ScheduleTriggerConfig(cron="0 9 * * *", timezone="UTC"),
    ),
    nodes=[
        WorkflowNodeDSL(
            id="trigger_daily",
            type=NodeType.trigger,
            service=ServiceType.scheduler,
            operation=OperationType.cron,
            label="Daily at 9 AM",
            params={"cron": "0 9 * * *", "timezone": "UTC"},
            on_success="read_appointments",
        ),
        WorkflowNodeDSL(
            id="read_appointments",
            type=NodeType.action,
            service=ServiceType.google_sheets,
            operation=OperationType.read_rows,
            label="Read Today's Appointments",
            params={
                "spreadsheet_id": "{{env.APPOINTMENTS_SHEET_ID}}",
                "range": "Sheet1!A:E",
                "filter": {
                    "column": "appointment_date",
                    "equals": "{{context.tomorrow_date}}"
                },
            },
            on_success="check_has_appointments",
            on_failure="log_error",
            retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=30),
        ),
        WorkflowNodeDSL(
            id="check_has_appointments",
            type=NodeType.condition,
            service=ServiceType.builtin,
            operation=OperationType.condition_branch,
            label="Are There Appointments?",
            params={
                "condition": "{{read_appointments.output.row_count > 0}}",
            },
            on_success="loop_patients",
            on_failure=None,
        ),
        WorkflowNodeDSL(
            id="loop_patients",
            type=NodeType.loop,
            service=ServiceType.builtin,
            operation=OperationType.for_each,
            label="For Each Patient",
            params={
                "items": "{{read_appointments.output.rows}}",
                "item_var": "patient",
            },
            on_success="send_reminder_email",
        ),
        WorkflowNodeDSL(
            id="send_reminder_email",
            type=NodeType.action,
            service=ServiceType.gmail,
            operation=OperationType.send_email,
            label="Send Reminder Email",
            params={
                "to": "{{patient.email}}",
                "subject": "Reminder: Your appointment is tomorrow",
                "body": (
                    "Dear {{patient.name}},\n\n"
                    "This is a reminder that you have an appointment scheduled for "
                    "{{patient.appointment_date}} at {{patient.appointment_time}}.\n\n"
                    "Please arrive 10 minutes early. If you need to reschedule, "
                    "please call us at {{env.CLINIC_PHONE}}.\n\n"
                    "Best regards,\n{{env.CLINIC_NAME}}"
                ),
            },
            on_success=None,
            on_failure="log_error",
            retry_policy=RetryPolicy(max_attempts=2, backoff_seconds=60),
        ),
        WorkflowNodeDSL(
            id="log_error",
            type=NodeType.action,
            service=ServiceType.builtin,
            operation=OperationType.set_variable,
            label="Log Error",
            params={
                "variable": "last_error",
                "value": "{{context.error_message}}",
            },
        ),
    ],
    edges=[
        WorkflowEdgeDSL(source_id="trigger_daily",           target_id="read_appointments"),
        WorkflowEdgeDSL(source_id="read_appointments",        target_id="check_has_appointments"),
        WorkflowEdgeDSL(source_id="check_has_appointments",   target_id="loop_patients",       label="true",  condition="{{read_appointments.output.row_count > 0}}"),
        WorkflowEdgeDSL(source_id="check_has_appointments",   target_id="log_error",           label="false"),
        WorkflowEdgeDSL(source_id="loop_patients",            target_id="send_reminder_email"),
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# EXAMPLE B: Weekly Business Report Workflow
# Trigger: Every Monday at 8 AM UTC
# Flow: Pull KPIs from Sheets → AI generates summary → send email to manager
# ─────────────────────────────────────────────────────────────────────────────

WEEKLY_REPORT_DSL = WorkflowDSL(
    id="example-weekly-report",
    name="Weekly Business Report",
    description=(
        "Every Monday, fetches KPI data from Google Sheets, uses AI to generate "
        "a concise executive summary, and emails it to the management team."
    ),
    industry="business",
    version=1,
    tags=["reports", "analytics", "email", "ai", "weekly"],
    trigger=TriggerConfig(
        type=TriggerType.schedule,
        config=ScheduleTriggerConfig(cron="0 8 * * 1", timezone="UTC"),
    ),
    nodes=[
        WorkflowNodeDSL(
            id="trigger_monday",
            type=NodeType.trigger,
            service=ServiceType.scheduler,
            operation=OperationType.cron,
            label="Every Monday at 8 AM",
            params={"cron": "0 8 * * 1", "timezone": "UTC"},
            on_success="fetch_kpi_data",
        ),
        WorkflowNodeDSL(
            id="fetch_kpi_data",
            type=NodeType.action,
            service=ServiceType.google_sheets,
            operation=OperationType.read_rows,
            label="Fetch Weekly KPIs",
            params={
                "spreadsheet_id": "{{env.KPI_SHEET_ID}}",
                "range": "KPIs!A1:G50",
                "filter": {
                    "column": "week",
                    "equals": "{{context.current_week_number}}",
                },
            },
            on_success="ai_generate_summary",
            on_failure="notify_error",
            retry_policy=RetryPolicy(max_attempts=3, backoff_seconds=60),
        ),
        WorkflowNodeDSL(
            id="ai_generate_summary",
            type=NodeType.ai_agent,
            service=ServiceType.groq,
            operation=OperationType.llm_generate,
            label="AI: Generate Executive Summary",
            params={
                "model": "llama-3.3-70b-versatile",
                "system_prompt": (
                    "You are a business analyst. Given weekly KPI data, "
                    "write a concise 3-paragraph executive summary highlighting "
                    "top wins, concerns, and recommended actions."
                ),
                "user_prompt": (
                    "Here is this week's KPI data:\n{{fetch_kpi_data.output.rows | tojson}}\n\n"
                    "Write the executive summary now."
                ),
                "max_tokens": 600,
                "temperature": 0.4,
            },
            on_success="send_report_email",
            on_failure="notify_error",
            timeout_seconds=60,
        ),
        WorkflowNodeDSL(
            id="send_report_email",
            type=NodeType.action,
            service=ServiceType.gmail,
            operation=OperationType.send_email,
            label="Email Report to Management",
            params={
                "to": "{{env.MANAGEMENT_EMAIL}}",
                "cc": "{{env.MANAGEMENT_CC_LIST}}",
                "subject": "📊 Weekly Business Report — Week {{context.current_week_number}}",
                "body": (
                    "Dear Team,\n\n"
                    "{{ai_generate_summary.output.text}}\n\n"
                    "---\n"
                    "Full KPI data is available in the dashboard.\n"
                    "This report was auto-generated by AutoFlow AI X."
                ),
            },
            on_success="log_success",
            on_failure="notify_error",
        ),
        WorkflowNodeDSL(
            id="log_success",
            type=NodeType.action,
            service=ServiceType.google_sheets,
            operation=OperationType.append_row,
            label="Log Run to Audit Sheet",
            params={
                "spreadsheet_id": "{{env.AUDIT_SHEET_ID}}",
                "range": "RunLog!A:D",
                "row": {
                    "date": "{{context.today}}",
                    "workflow": "Weekly Report",
                    "status": "success",
                    "recipients": "{{env.MANAGEMENT_EMAIL}}",
                },
            },
        ),
        WorkflowNodeDSL(
            id="notify_error",
            type=NodeType.action,
            service=ServiceType.gmail,
            operation=OperationType.send_email,
            label="Notify Admin of Error",
            params={
                "to": "{{env.ADMIN_EMAIL}}",
                "subject": "⚠️ AutoFlow Error: Weekly Report Failed",
                "body": "The Weekly Business Report workflow failed.\n\nError: {{context.error_message}}",
            },
        ),
    ],
    edges=[
        WorkflowEdgeDSL(source_id="trigger_monday",       target_id="fetch_kpi_data"),
        WorkflowEdgeDSL(source_id="fetch_kpi_data",       target_id="ai_generate_summary"),
        WorkflowEdgeDSL(source_id="ai_generate_summary",  target_id="send_report_email"),
        WorkflowEdgeDSL(source_id="send_report_email",    target_id="log_success"),
    ],
)


def get_example_dsl_json(name: str = "appointment") -> dict:
    """Return a serialized example DSL dict for use in prompts or API responses."""
    examples = {
        "appointment": APPOINTMENT_REMINDER_DSL,
        "weekly_report": WEEKLY_REPORT_DSL,
    }
    dsl = examples.get(name, APPOINTMENT_REMINDER_DSL)
    return dsl.model_dump(mode="json")
