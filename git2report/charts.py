"""Visual analytics and chart generators for Git2Report.

Renders vector drawings for ReportLab PDF and embedded responsive SVG/HTML charts
without requiring external heavy chart dependencies.
"""
from __future__ import annotations

import math
from typing import Any

from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Group, Line, Rect, String


TYPE_COLORS = {
    "feat": colors.HexColor("#059669"),      # Emerald Green
    "fix": colors.HexColor("#DC2626"),       # Red
    "perf": colors.HexColor("#7C3AED"),      # Purple
    "refactor": colors.HexColor("#D97706"),  # Amber
    "docs": colors.HexColor("#0284C7"),      # Cyan
    "test": colors.HexColor("#0D9488"),      # Teal
    "style": colors.HexColor("#64748B"),     # Slate
    "chore": colors.HexColor("#94A3B8"),     # Light Slate
    "other": colors.HexColor("#3B82F6"),     # Blue
}


def build_type_breakdown_bar(commits_by_type: dict[str, int], width: float = 490, height: float = 38) -> Drawing:
    """Creates a sleek, segmented horizontal bar drawing showing commit type percentages."""
    d = Drawing(width, height)
    total = sum(commits_by_type.values())
    if total <= 0:
        return d

    bar_y = 16
    bar_h = 14
    cur_x = 0.0

    # Draw segments
    for ctype, count in commits_by_type.items():
        if count <= 0:
            continue
        seg_w = (count / total) * width
        color = TYPE_COLORS.get(ctype.lower(), TYPE_COLORS["other"])
        d.add(Rect(cur_x, bar_y, seg_w, bar_h, fillColor=color, strokeColor=colors.white, strokeWidth=1))
        
        # Label percentage inside segment if wide enough
        if seg_w > 26:
            pct_text = f"{int(round((count / total) * 100))}%"
            d.add(String(cur_x + seg_w / 2, bar_y + 3.5, pct_text, textAnchor="middle",
                         fontName="Helvetica-Bold", fontSize=7.5, fillColor=colors.white))
        cur_x += seg_w

    # Draw Legend below the bar
    leg_x = 0.0
    for ctype, count in list(commits_by_type.items())[:6]:
        if count <= 0:
            continue
        color = TYPE_COLORS.get(ctype.lower(), TYPE_COLORS["other"])
        # Dot
        d.add(Rect(leg_x, 3, 7, 7, fillColor=color, strokeColor=color, rx=1.5, ry=1.5))
        label = f"{ctype.upper()} ({count})"
        d.add(String(leg_x + 10, 3, label, fontName="Helvetica", fontSize=7, fillColor=colors.HexColor("#475569")))
        leg_x += len(label) * 4.4 + 16

    return d


def build_module_churn_chart(sections: list[Any], width: float = 490, height: float = 85) -> Drawing:
    """Creates a horizontal vector bar chart showing code churn (+added / -deleted) per module."""
    d = Drawing(width, height)
    if not sections:
        return d

    # Collect up to 4 top modules by line changes
    module_data = []
    for s in sections[:4]:
        added = sum(getattr(cm, "added", 0) for cm in getattr(s, "commits", []))
        deleted = sum(getattr(cm, "deleted", 0) for cm in getattr(s, "commits", []))
        module_data.append((s.module, added, deleted))

    if not module_data:
        return d

    max_val = max(max(a, d_) for _, a, d_ in module_data) or 1
    row_h = 16
    start_y = height - 12
    label_w = 90
    bar_max_w = width - label_w - 45

    green = colors.HexColor("#059669")
    red = colors.HexColor("#DC2626")

    for i, (mod, added, deleted) in enumerate(module_data):
        y = start_y - (i * (row_h + 3))

        # Module Name label
        mod_name = mod[:14] + ".." if len(mod) > 16 else mod
        d.add(String(0, y + 2, mod_name, fontName="Helvetica-Bold", fontSize=7.5, fillColor=colors.HexColor("#1E293B")))

        # Added bar (Green)
        w_add = max(2.0, (added / max_val) * (bar_max_w / 2)) if added > 0 else 0
        if w_add > 0:
            d.add(Rect(label_w, y, w_add, 7, fillColor=green, strokeColor=green, rx=1, ry=1))

        # Deleted bar (Red)
        w_del = max(2.0, (deleted / max_val) * (bar_max_w / 2)) if deleted > 0 else 0
        if w_del > 0:
            d.add(Rect(label_w + w_add + 4, y, w_del, 7, fillColor=red, strokeColor=red, rx=1, ry=1))

        # Stat text
        stat_text = f"+{added} / -{deleted}"
        d.add(String(label_w + w_add + w_del + 10, y + 1, stat_text, fontName="Courier", fontSize=6.5, fillColor=colors.HexColor("#64748B")))

    return d


def generate_svg_churn_chart(sections: list[Any]) -> str:
    """Generates an embedded responsive SVG for the interactive HTML report dashboard."""
    module_data = []
    for s in sections[:5]:
        added = sum(getattr(cm, "added", 0) for cm in getattr(s, "commits", []))
        deleted = sum(getattr(cm, "deleted", 0) for cm in getattr(s, "commits", []))
        module_data.append((s.module, added, deleted))

    if not module_data:
        return ""

    max_val = max(max(a, d_) for _, a, d_ in module_data) or 1
    svg_height = len(module_data) * 36 + 20
    rows = []

    for i, (mod, added, deleted) in enumerate(module_data):
        y = 20 + i * 36
        w_add = (added / max_val) * 220 if added > 0 else 0
        w_del = (deleted / max_val) * 220 if deleted > 0 else 0

        rows.append(f"""
          <g class="chart-row">
            <text x="0" y="{y + 14}" fill="currentColor" font-size="12" font-weight="600">{mod}</text>
            <rect x="130" y="{y}" width="{w_add:.1f}" height="16" rx="3" fill="#10b981" opacity="0.9">
              <title>Added: +{added} lines</title>
            </rect>
            <rect x="{135 + w_add:.1f}" y="{y}" width="{w_del:.1f}" height="16" rx="3" fill="#ef4444" opacity="0.9">
              <title>Deleted: -{deleted} lines</title>
            </rect>
            <text x="{145 + w_add + w_del:.1f}" y="{y + 13}" fill="var(--text-muted)" font-size="11" font-family="monospace">+{added} / -{deleted}</text>
          </g>
        """)

    return f"""
    <svg viewBox="0 0 650 {svg_height}" width="100%" height="{svg_height}" xmlns="http://www.w3.org/2000/svg" style="overflow: visible;">
      {''.join(rows)}
    </svg>
    """
