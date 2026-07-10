"""
Exports a scan's shortlist to files the editorial team can actually work
with: a CSV (to open in Excel/Google Sheets and mark selections) and a
Markdown summary (to skim quickly). No paid tools involved.
"""

import csv
from pathlib import Path

CATEGORY_LABELS = {
    "local_online": "Local Media - Online",
    "international": "International Media",
    "research": "Research Findings",
}


def export_csv(items, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "include", "section", "source_name", "title", "url", "language",
        "published_at", "covered_by_count", "highlight_score", "matched_keywords",
        "editor_summary",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            writer.writerow({
                "include": "",  # editor fills in Y/N
                "section": CATEGORY_LABELS.get(item.get("source_category"), item.get("source_category")),
                "source_name": item.get("source_name", ""),
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "language": item.get("language", ""),
                "published_at": item.get("published_at").isoformat() if item.get("published_at") else "",
                "covered_by_count": len(item.get("covered_by", [item.get("source_name", "")])),
                "highlight_score": item.get("highlight_score", ""),
                "matched_keywords": ", ".join(item.get("matched_keywords", [])),
                "editor_summary": "",  # editor writes the report-style summary here
            })
    return out_path


def export_markdown(items, out_path, scan_info):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    by_category = {}
    for item in items:
        by_category.setdefault(item.get("source_category", "other"), []).append(item)

    lines = [
        f"# Health Media Shortlist -- {scan_info['mode'].title()} scan",
        f"Window: {scan_info['window_start']} to {scan_info['window_end']}",
        f"Raw items collected: {scan_info.get('raw_items_collected', '?')} | "
        f"Relevant: {scan_info.get('relevant_items', '?')} | "
        f"Unique after dedup: {scan_info.get('unique_items', '?')}",
        "",
    ]

    for category, label in CATEGORY_LABELS.items():
        cat_items = by_category.get(category, [])
        if not cat_items:
            continue
        lines.append(f"## {label} ({len(cat_items)})")
        for item in cat_items:
            covered = item.get("covered_by", [item.get("source_name", "")])
            covered_note = f" -- also covered by {len(covered) - 1} other outlet(s)" if len(covered) > 1 else ""
            lines.append(f"- **{item['title']}** ({item.get('source_name', '')}){covered_note}")
            lines.append(f"  {item['url']}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path
