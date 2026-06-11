from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import get_settings


def _equity_chart(backtest: dict) -> BytesIO:
    fig, ax = plt.subplots(figsize=(7.5, 2.4), facecolor="#ffffff")
    ax.set_facecolor("#ffffff")
    gross = [point["gross"] for point in backtest["equityCurve"]]
    net = [point["net"] for point in backtest["equityCurve"]]
    ax.plot(gross, color="#0b6bcb", linewidth=2, label="Gross")
    ax.plot(net, color="#047857", linewidth=2, label="Net")
    ax.grid(color="#d7dde8", alpha=0.65)
    ax.tick_params(colors="#111827")
    for spine in ax.spines.values():
        spine.set_color("#c7cedb")
    ax.legend(facecolor="#ffffff", edgecolor="#c7cedb", labelcolor="#111827")
    fig.tight_layout()
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=200)
    plt.close(fig)
    buffer.seek(0)
    return buffer


def export_investment_note(*, symbol_meta, signal: dict, backtest: dict, news: list[dict]) -> Path:
    settings = get_settings()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output = settings.resolved_artefacts_dir / "exports" / f"{symbol_meta.symbol.upper()}-investment-note-{timestamp}.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="HeadingPrint",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#111827"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyPrint",
            parent=styles["BodyText"],
            textColor=colors.HexColor("#1f2937"),
            leading=14,
        )
    )

    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    story = [
        Paragraph(f"Markets Strategy Copilot: {symbol_meta.symbol} Investment Note", styles["HeadingPrint"]),
        Paragraph(
            f"{symbol_meta.name} | {symbol_meta.asset_class} | Current action: <b>{signal['action']}</b> with confidence <b>{signal['confidence']:.0%}</b>.",
            styles["BodyPrint"],
        ),
        Spacer(1, 10),
    ]

    summary_table = Table(
        [
            ["Current price", f"{signal['currentPrice']:.4f}", "Regime", signal["regime"]],
            ["Stop / invalidation", f"{signal['stopLoss'] or 'n/a'}", "Take-profit zone", f"{signal['takeProfitLow'] or 'n/a'} -> {signal['takeProfitHigh'] or 'n/a'}"],
            ["Position size", f"{signal['positionSizePct']:.1%}", "Freshness", f"{signal['dataFreshnessSeconds']:.0f}s"],
        ],
        colWidths=[120, 120, 120, 150],
    )
    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, -1), colors.white),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#111827")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]
    )
    summary_table.setStyle(table_style)
    story.extend([summary_table, Spacer(1, 12)])

    if signal.get("dataQuality"):
        story.append(Paragraph("Data quality and source readiness", styles["HeadingPrint"]))
        quality = signal["dataQuality"]
        story.append(Paragraph(f"Quality score: <b>{quality['score']}/100</b> ({quality['label']}).", styles["BodyPrint"]))
        for factor in quality.get("factors", [])[:5]:
            story.append(Paragraph(f"- <b>{factor['label']}</b>: {factor['detail']}", styles["BodyPrint"]))
        story.append(Spacer(1, 8))

    if signal.get("waterfall"):
        story.append(Paragraph("Confidence waterfall", styles["HeadingPrint"]))
        waterfall_rows = [["Component", "Impact", "Type"]]
        for item in signal["waterfall"].get("items", [])[:10]:
            waterfall_rows.append([item["label"], f"{item['value']:+.2f}", item["kind"]])
        waterfall_table = Table(waterfall_rows, colWidths=[270, 90, 120])
        waterfall_table.setStyle(table_style)
        story.extend([waterfall_table, Spacer(1, 10)])

    story.append(Paragraph("Signal rationale", styles["HeadingPrint"]))
    for reason in signal["reasonCodes"][:5]:
        story.append(Paragraph(f"- <b>{reason['label']}</b>: {reason['detail']}", styles["BodyPrint"]))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Risk flags", styles["HeadingPrint"]))
    if signal["riskFlags"]:
        for flag in signal["riskFlags"]:
            story.append(Paragraph(f"- <b>{flag['code']}</b>: {flag['message']}", styles["BodyPrint"]))
    else:
        story.append(Paragraph("- No active risk flags in the current snapshot.", styles["BodyPrint"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("TCA-aware performance snapshot", styles["HeadingPrint"]))
    metrics = backtest["metrics"]
    metrics_table = Table(
        [
            ["Total return", f"{metrics['totalReturn']:.2%}", "Gross return", f"{metrics['grossReturn']:.2%}"],
            ["Sharpe", f"{metrics['sharpe']:.2f}", "Max drawdown", f"{metrics['maxDrawdown']:.2%}"],
            ["Turnover", f"{metrics['turnover']:.2f}", "Exposure", f"{metrics['exposure']:.2%}"],
        ],
        colWidths=[120, 110, 120, 110],
    )
    metrics_table.setStyle(table_style)
    story.extend([metrics_table, Spacer(1, 10)])

    story.append(Image(_equity_chart(backtest), width=510, height=162))
    story.append(Spacer(1, 10))

    story.append(Paragraph("News citations", styles["HeadingPrint"]))
    for item in news[:4]:
        story.append(Paragraph(f"- {item['title']} ({item['source']})", styles["BodyPrint"]))

    doc.build(story)
    return output
