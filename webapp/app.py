"""
Local web app for reviewing scan results in a browser instead of a CSV.

Runs entirely on your own machine -- no cloud hosting, no cost. Reads and
writes the same SQLite database (media_monitor.db) that scan.py produces,
so nothing about the scanning pipeline changes; this is purely a nicer way
to look at and act on the results.

Run with:
    python webapp/app.py

Then open http://127.0.0.1:5000 in your browser.
"""

import os
import sys
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, send_file

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import db  # noqa: E402
import config  # noqa: E402
import report_generator  # noqa: E402
import scan as scan_module  # noqa: E402

app = Flask(__name__)
app.secret_key = "dev-only-not-used-for-anything-sensitive"  # fine for a local-only tool

CATEGORY_LABELS = {
    "local_online": "Local Media - Online",
    "international": "International Media",
    "research": "Research Findings",
}
CATEGORY_ORDER = ["local_online", "international", "research"]


@app.route("/")
def index():
    db.init_db()
    scans = db.list_scans()
    return render_template("index.html", scans=scans)


@app.route("/scan/<int:scan_id>")
def view_scan(scan_id):
    scan_info = db.get_scan(scan_id)
    if not scan_info:
        flash(f"No scan found with id {scan_id}")
        return redirect(url_for("index"))

    items = db.get_items_for_scan(scan_id)

    # Group by section, in the report's standard order
    grouped = {cat: [] for cat in CATEGORY_ORDER}
    for item in items:
        grouped.setdefault(item["source_category"], []).append(item)

    # Within each section, show highest highlight_score first
    for cat in grouped:
        grouped[cat].sort(key=lambda i: (i["highlight_score"] or 0), reverse=True)

    included_count = sum(1 for i in items if i.get("included") == 1)
    
    # Parse and prepare source_counts from scan's stored JSON
    import json
    source_counts = {}
    if scan_info.get("source_counts"):
        try:
            source_counts = json.loads(scan_info["source_counts"]) if isinstance(scan_info["source_counts"], str) else scan_info["source_counts"]
        except (json.JSONDecodeError, TypeError):
            source_counts = {}

    return render_template(
        "scan.html",
        scan=scan_info,
        grouped=grouped,
        category_labels=CATEGORY_LABELS,
        category_order=CATEGORY_ORDER,
        total_items=len(items),
        included_count=included_count,
        source_counts=source_counts,
    )


@app.route("/scan/<int:scan_id>/save", methods=["POST"])
def save_review(scan_id):
    items = db.get_items_for_scan(scan_id)
    for item in items:
        item_id = item["id"]
        included = request.form.get(f"include_{item_id}")  # "on" if checked, None if not
        summary = request.form.get(f"summary_{item_id}", "").strip()
        db.update_item_review(
            item_id,
            included=1 if included == "on" else 0,
            editor_summary=summary,
        )
    flash("Review saved.")
    return redirect(url_for("view_scan", scan_id=scan_id))


@app.route("/scan/<int:scan_id>/delete", methods=["POST"])
def delete_scan_route(scan_id):
    deleted = db.delete_scan(scan_id)
    if deleted:
        flash(f"Scan {scan_id} deleted.")
    else:
        flash(f"No scan found with id {scan_id}.")
    return redirect(url_for("index"))


@app.route("/delete-all-scans", methods=["POST"])
def delete_all_scans_route():
    count = db.delete_all_scans()
    flash(f"Deleted all {count} scan(s).")
    return redirect(url_for("index"))


@app.route("/new-scan")
def new_scan_form():
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("new_scan.html", today=today)


@app.route("/run-scan", methods=["POST"])
def run_scan_route():
    mode = request.form.get("mode")
    if mode not in ("daily", "weekly"):
        flash("Please choose a scan type (daily or weekly).")
        return redirect(url_for("new_scan_form"))

    date_str = request.form.get("date", "").strip()
    start_date_str = request.form.get("start_date", "").strip()

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else None
    except ValueError:
        flash("That doesn't look like a valid date. Please use the date picker.")
        return redirect(url_for("new_scan_form"))

    try:
        result = scan_module.run_scan(mode, target_date=target_date, start_date=start_date)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("new_scan_form"))
    except Exception as exc:  # noqa: BLE001 -- surface unexpected failures to the user, don't crash silently
        flash(f"Scan failed to complete: {exc}")
        return redirect(url_for("new_scan_form"))

    diag = result["diagnostics"]
    if diag["raw_items"] == 0:
        flash(
            "Scan finished but collected 0 raw items from every source -- this usually means "
            "a network/access problem, not a lack of news. Check the terminal running the web "
            "app for WARNING lines explaining why each collector failed."
        )
    elif diag["unique_items"] == 0:
        flash(
            f"Scan finished but the shortlist is empty. Collected {diag['raw_items']} items "
            f"({diag['windowed_items']} within the date window, {diag['relevant_items']} matched "
            "health keywords). Check the terminal log for details on where items were filtered out."
        )
    else:
        by_section = ", ".join(f"{k}: {v}" for k, v in diag["category_counts"].items()) or "none"
        flash(f"Scan complete: {len(result['ranked_items'])} items in the shortlist ({by_section}).")

    return redirect(url_for("view_scan", scan_id=result["scan_id"]))




@app.route("/scan/<int:scan_id>/generate-report")
def generate_report(scan_id):
    try:
        out_path = report_generator.generate_report(scan_id)
    except ValueError as exc:
        flash(str(exc))
        return redirect(url_for("view_scan", scan_id=scan_id))

    # Flask/Werkzeug resolves relative paths against the app's root_path
    # (the webapp/ folder), not the process's working directory -- send an
    # absolute path so this works regardless of where the app was launched from.
    return send_file(os.path.abspath(out_path), as_attachment=True)


if __name__ == "__main__":
    import os
    db.init_db()
    # In production, gunicorn will handle the PORT env var via Procfile
    # In development, use port 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
