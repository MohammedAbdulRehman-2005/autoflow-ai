"""
Migration: patch_slack_channel.py
==================================
Finds every saved workflow whose DSL contains a Slack post_message node
with channel='#general' and updates it to '#all-autoflow-ai'.

Run once on the Railway Postgres DB:
    python patch_slack_channel.py

Set DATABASE_URL in your environment (same value as on Railway).
"""
import json
import os
import sys

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL env var is not set.")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

PATCH_FROM = "#general"
PATCH_TO   = "#all-autoflow-ai"

with engine.begin() as conn:
    rows = conn.execute(
        text("SELECT id, name, ai_context_json FROM workflows WHERE ai_context_json IS NOT NULL")
    ).fetchall()

    patched = 0
    for row in rows:
        wf_id, wf_name, dsl_json = row
        dsl = dsl_json if isinstance(dsl_json, dict) else json.loads(dsl_json)

        changed = False
        for node in dsl.get("nodes", []):
            params = node.get("params", {})
            if node.get("operation") == "post_message" and params.get("channel") == PATCH_FROM:
                params["channel"] = PATCH_TO
                node["params"] = params
                changed = True
                print(f"  Patching node '{node['id']}' in workflow '{wf_name}' ({wf_id})")

        if changed:
            conn.execute(
                text("UPDATE workflows SET ai_context_json = :dsl WHERE id = :id"),
                {"dsl": json.dumps(dsl), "id": str(wf_id)},
            )
            patched += 1

    print(f"\nDone. {patched} workflow(s) patched.")
