"""Generates a professional, comprehensive College Presentation and Self-Run Guide PDF for Git2Report."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def make_guide_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Git2Report — College Presentation & Operation Guide",
    )

    ss = getSampleStyleSheet()
    navy = colors.HexColor("#0F172A")
    blue = colors.HexColor("#2563EB")
    light_blue = colors.HexColor("#EFF6FF")
    slate = colors.HexColor("#334155")
    gray_bg = colors.HexColor("#F8FAFC")
    gray_border = colors.HexColor("#CBD5E1")
    green = colors.HexColor("#059669")
    green_bg = colors.HexColor("#F0FDF4")
    amber = colors.HexColor("#D97706")
    amber_bg = colors.HexColor("#FFFBEB")

    # Typography styles
    title_style = ParagraphStyle("DocTitle", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=navy, alignment=0, spaceAfter=4)
    subtitle_style = ParagraphStyle("DocSub", parent=ss["Normal"], fontName="Helvetica", fontSize=11, leading=15, textColor=blue, spaceAfter=8)
    meta_style = ParagraphStyle("Meta", parent=ss["Normal"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=colors.HexColor("#64748B"), spaceAfter=12)

    h1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=navy, spaceBefore=12, spaceAfter=6)
    h2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=blue, spaceBefore=8, spaceAfter=4)
    
    body = ParagraphStyle("Body", parent=ss["Normal"], fontName="Helvetica", fontSize=9, leading=13.5, textColor=slate)
    body_bold = ParagraphStyle("BodyB", parent=body, fontName="Helvetica-Bold", textColor=navy)
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=12, bulletIndent=4, spaceAfter=3)

    code_block = ParagraphStyle("Code", parent=ss["Normal"], fontName="Courier", fontSize=8, leading=11, textColor=colors.HexColor("#0F172A"))
    
    table_cell = ParagraphStyle("TableCell", parent=ss["Normal"], fontName="Helvetica", fontSize=8.5, leading=11, textColor=slate)
    table_cell_b = ParagraphStyle("TableCellB", parent=table_cell, fontName="Helvetica-Bold", textColor=navy)
    table_cell_h = ParagraphStyle("TableCellH", parent=table_cell, fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white)

    story = []

    # ==========================================
    # COVER / HEADER
    # ==========================================
    story.append(Paragraph("Git2Report: Project Presentation &amp; Viva Guide", title_style))
    story.append(Paragraph("Complete College Defense Pitch, Architectural Overview &amp; Self-Execution Manual", subtitle_style))
    story.append(Paragraph("<b>Target Audience:</b> Project Evaluators, College Viva Panel, External Examiners &amp; Developers &nbsp;|&nbsp; <b>Version:</b> 1.0 Production", meta_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=blue, spaceAfter=10))

    # Executive Overview Callout
    callout_data = [
        [Paragraph("<b>PROJECT AT A GLANCE (THE ELEVATOR PITCH)</b>", ParagraphStyle("CH", parent=body, fontName="Helvetica-Bold", fontSize=9, textColor=colors.HexColor("#1E40AF")))],
        [Paragraph(
            "<b>Git2Report</b> is a production-grade developer tool that converts raw, chaotic Git version control histories "
            "into executive-ready, plain-language engineering progress reports in <b>final PDF format</b>. "
            "Unlike simple LLM chat wrappers, Git2Report uses a <b>deterministic hybrid architecture</b>: numbers and metrics "
            "(churn, active modules, test ratio, commit counts) are strictly calculated via Git tree analysis and can never hallucinate, "
            "while Google Gemini AI translates technical diffs into human-readable business English with strict commit hash traceability.",
            body
        )]
    ]
    callout_tbl = Table(callout_data, colWidths=[17.4 * cm])
    callout_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_blue),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFDBFE")),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, blue),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(callout_tbl)
    story.append(Spacer(1, 10))

    # ==========================================
    # SECTION 1: PROBLEM & MOTIVATION
    # ==========================================
    story.append(Paragraph("1. The Real-World Problem We Solved", h1))
    story.append(Paragraph(
        "Software engineering teams face a major communication gap between developers and stakeholders:",
        body
    ))
    story.append(Spacer(1, 4))

    prob_rows = [
        [Paragraph("The Industry Problem", table_cell_h), Paragraph("Why Existing Solutions Fail", table_cell_h), Paragraph("How Git2Report Solves It", table_cell_h)],
        [
            Paragraph("<b>Wasted Developer Time:</b> Engineers spend 3–5 hours each week manually drafting status reports.", table_cell),
            Paragraph("Manual reporting relies on memory and subjective descriptions without verification.", table_cell),
            Paragraph("<b>1-Click Autonomous Extraction:</b> Directly mines Git commit logs, eliminating manual reporting entirely.", table_cell),
        ],
        [
            Paragraph("<b>Unreadable Technical Jargon:</b> Clients &amp; project guides cannot understand commit messages like <i>'fix: auth err'</i> or <i>'wip'</i>.", table_cell),
            Paragraph("Raw Git log viewers dump unformatted technical text without business context.", table_cell),
            Paragraph("<b>Plain-Language AI Summaries:</b> AI translates diffs into executive-level English (e.g. <i>'Implemented JWT security with bcrypt password hashing'</i>).", table_cell),
        ],
        [
            Paragraph("<b>AI Hallucination Risk:</b> ChatGPT/Claude invent non-existent statistics or fake commit numbers when fed logs.", table_cell),
            Paragraph("Generic LLMs have no grounding in the repository's ground-truth Git DAG tree.", table_cell),
            Paragraph("<b>Anti-Hallucination Guardrails:</b> Numbers and lines are 100% computed in Python; LLM only writes sentences.", table_cell),
        ],
    ]
    prob_tbl = Table(prob_rows, colWidths=[5.4 * cm, 5.8 * cm, 6.2 * cm])
    prob_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, gray_bg]),
        ("GRID", (0, 0), (-1, -1), 0.5, gray_border),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(prob_tbl)
    story.append(Spacer(1, 10))

    # ==========================================
    # SECTION 2: 7-STEP ARCHITECTURE
    # ==========================================
    story.append(Paragraph("2. Technical Architecture: The 7-Step Pipeline", h1))
    story.append(Paragraph(
        "Explain to the panel that Git2Report is an end-to-end engineered compiler with seven discrete stages:",
        body
    ))
    story.append(Spacer(1, 4))

    steps_data = [
        ("Step 1: Commit Mining &amp; Ingestion", "Uses <code>PyDriller</code> &amp; <code>GitPython</code> to traverse commits and parse file-level diff trees across branches."),
        ("Step 2: Intelligent Noise Filtering", "Discards merge commits, lockfiles (package-lock.json), build directories, and zero-value 'wip/typo' commits."),
        ("Step 3: Architectural Clustering", "Groups commits by module path (Backend, Frontend, Auth, Database) using path topology rather than arbitrary rules."),
        ("Step 4: Metric &amp; Churn Computation", "Calculates net code churn (+added / -deleted), test-to-code ratio, contributor stats, and tech stack percentages."),
        ("Step 5: Diff Chunking &amp; Formatting", "Sanitizes diffs and truncates oversized payloads to stay within strict LLM token context limits."),
        ("Step 6: AI Synthesis with Auto-Fallback", "Google Gemini converts verified diffs into plain English. If rate-limited (429/503), it auto-cascades to fallback models or offline synthesis."),
        ("Step 7: Production PDF Rendering", "ReportLab compiles executive summaries, KPI tables, codebase hotspots, and color-coded badges directly into a clean PDF."),
    ]
    for s_title, s_desc in steps_data:
        story.append(Paragraph(f"• <b>{s_title}</b>: {s_desc}", bullet))

    story.append(Spacer(1, 10))

    # ==========================================
    # PAGE 2: HOW TO RUN IN POWERSHELL
    # ==========================================
    story.append(PageBreak())
    story.append(Paragraph("3. How to Run It Yourself (PowerShell Manual)", h1))
    story.append(Paragraph(
        "Follow these exact steps in your terminal. You can run it on your current repository or any public GitHub repository:",
        body
    ))
    story.append(Spacer(1, 6))

    # Command Box 1
    c1 = (
        "# 1. Open PowerShell and navigate to the project directory\n"
        "cd c:\\Users\\CC\\OneDrive\\Desktop\\Project\\git2report\n\n"
        "# 2. Activate the Python virtual environment\n"
        ".\\.venv\\Scripts\\Activate.ps1\n\n"
        "# 3. Run on the current repository with AI summarization:\n"
        "git2report --repo . --llm\n"
        "# -> Output: Generates 'report.pdf' directly in your directory!"
    )
    cmd1_tbl = Table([[Paragraph(esc(c1).replace("\n", "<br/>"), code_block)]], colWidths=[17.4 * cm])
    cmd1_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), gray_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, gray_border),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(cmd1_tbl)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Advanced Execution Scenarios:", h2))

    # Scenarios Table
    scenarios = [
        [Paragraph("Scenario", table_cell_h), Paragraph("PowerShell Command", table_cell_h), Paragraph("What It Does", table_cell_h)],
        [
            Paragraph("<b>Run on Any Remote GitHub Repo</b>", table_cell_b),
            Paragraph("<code>git2report --repo https://github.com/user/repo --since 2026-07-01 --llm</code>", table_cell),
            Paragraph("Automatically clones the remote repository into <code>cloned_repos/</code> and generates <code>report.pdf</code>.", table_cell),
        ],
        [
            Paragraph("<b>Lookback Window Adjustment</b>", table_cell_b),
            Paragraph("<code>git2report --since 14d --llm</code><br/><code>git2report --since 2026-01-01 --llm</code>", table_cell),
            Paragraph("Controls how far back in Git history to inspect: days (<code>7d</code>), weeks (<code>2w</code>), or specific ISO dates.", table_cell),
        ],
        [
            Paragraph("<b>Add Future Goals</b>", table_cell_b),
            Paragraph("<code>git2report --llm -n 'Deploy Redis cache' -n 'Integrate Stripe payments'</code>", table_cell),
            Paragraph("Appends developer-written upcoming milestones under the Planned Goals section of the PDF.", table_cell),
        ],
        [
            Paragraph("<b>Change Audience Perspective</b>", table_cell_b),
            Paragraph("<code>git2report --audience client --llm</code><br/><code>git2report --audience team --llm</code>", table_cell),
            Paragraph("Adapts vocabulary: <i>guide</i> (academic focus), <i>client</i> (business value), or <i>team</i> (technical details).", table_cell),
        ],
        [
            Paragraph("<b>100% Offline Mode (No Internet/API Key)</b>", table_cell_b),
            Paragraph("<code>git2report --repo .</code>", table_cell),
            Paragraph("Generates the full PDF report offline using synthesized sentence rules without making any external API calls.", table_cell),
        ],
    ]
    scen_tbl = Table(scenarios, colWidths=[4.2 * cm, 7.6 * cm, 5.6 * cm])
    scen_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, gray_bg]),
        ("GRID", (0, 0), (-1, -1), 0.5, gray_border),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(scen_tbl)
    story.append(Spacer(1, 10))

    # ==========================================
    # SECTION 4: COLLEGE VIVA & DEFENSE SCRIPT
    # ==========================================
    story.append(Paragraph("4. How to Present This in College (What to Say)", h1))
    story.append(Paragraph(
        "Use this structured script when explaining your project to your teacher, guide, or viva examiner:",
        body
    ))
    story.append(Spacer(1, 4))

    script_box = [
        [Paragraph("<b>RECOMMENDED 2-MINUTE VIVA INTRO:</b>", ParagraphStyle("SBH", parent=body, fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.HexColor("#065F46")))],
        [Paragraph(
            "<i>\"Respected professors, our project is <b>Git2Report</b>. In the software industry, engineering teams "
            "spend hours drafting weekly status updates, and clients or college guides struggle to understand messy commit messages.<br/><br/>"
            "We built an automated CLI tool that bridges this gap. When you run Git2Report on any repository or GitHub URL, "
            "it mines the Git commit history, filters out noise like merge conflicts and lockfiles, calculates exact code churn and test ratios, "
            "and uses Google Gemini to translate technical diffs into plain, professional English.<br/><br/>"
            "The critical innovation is our <b>Anti-Hallucination Architecture</b>: all metrics, commit counts, and lines changed are computed "
            "deterministically in Python directly from Git commit trees, meaning they can never be hallucinated. Every single claim in the report "
            "is cross-referenced with exact 7-character Git commit hashes. Finally, it compiles everything into a single, executive PDF report "
            "ready for management review.\"</i>",
            ParagraphStyle("ScriptBody", parent=body, fontSize=8.5, leading=12.5, textColor=colors.HexColor("#064E3B"))
        )]
    ]
    script_tbl = Table(script_box, colWidths=[17.4 * cm])
    script_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), green_bg),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#A7F3D0")),
        ("LINEBEFORE", (0, 0), (0, -1), 3.5, green),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(script_tbl)
    story.append(Spacer(1, 10))

    # ==========================================
    # PAGE 3: TOP 6 VIVA QUESTIONS & WINNING ANSWERS
    # ==========================================
    story.append(PageBreak())
    story.append(Paragraph("5. Top 6 Viva Questions &amp; Model Answers", h1))
    story.append(Paragraph(
        "Professors and external examiners typically ask these technical questions. Memorize these answers:",
        body
    ))
    story.append(Spacer(1, 6))

    viva_qa = [
        ("Q1: Why didn't you just paste git log into ChatGPT?",
         "Because generic LLMs fail at repository reporting: (1) token limits block repositories with hundreds of commits, "
         "(2) LLMs hallucinate numbers and file names, and (3) raw commit messages are often messy ('wip', 'asdf'). "
         "Git2Report acts as a deterministic compiler: it filters noise, clusters by architecture, computes exact metrics in Python, "
         "and only asks the LLM to write plain-language sentences from clean diffs."),
        ("Q2: How do you guarantee the AI doesn't hallucinate?",
         "We implement strict separation of concerns. All numerical KPIs (commits, lines added, lines deleted, test-to-code ratio, "
         "contributor leaderboard) are 100% computed in Python via PyDriller tree traversal. The AI has zero influence on the numbers. "
         "Furthermore, every deliverable is grounded by appending exact commit hashes directly from Git log."),
        ("Q3: What happens if there is no internet or the AI API fails?",
         "Git2Report is built with resilient fallbacks. If Gemini returns 429 quota limits or 503 errors, it automatically falls back "
         "to secondary models (gemini-3.5-flash-lite). If there is no internet at all, our offline rule synthesizer takes over, "
         "generating clean structured sentences using imperative verb rules and conventional commit prefixes."),
        ("Q4: How does your module clustering work?",
         "Rather than relying on arbitrary keywords, we use topological path analysis. Files in 'routes/', 'controllers/', or 'backend/' "
         "cluster into Backend; 'components/', 'views/', or 'src/' cluster into Frontend; test directories cluster into Tests. "
         "Commits touching multiple modules are weighted by changed line count to assign the dominant module."),
        ("Q5: What is the Test-to-Code ratio metric?",
         "It calculates the ratio of lines of test code modified versus feature code modified. A ratio around 1.0 indicates healthy "
         "test-driven development, whereas 0.0 indicates unverified code churn, giving management an objective measure of code quality."),
        ("Q6: How does the PDF generation work?",
         "We use ReportLab's Platypus flowable document engine. We construct dynamic tables, KPI grids, two-column analytics, "
         "and custom canvas callbacks for running headers and dynamic page numbering ('Page X'). Everything is generated in-memory "
         "and output directly as a final PDF without intermediate HTML/Markdown files."),
    ]

    for q, a in viva_qa:
        q_box = [
            [Paragraph(f"<b>{esc(q)}</b>", ParagraphStyle("QH", parent=body, fontName="Helvetica-Bold", fontSize=8.5, textColor=navy))],
            [Paragraph(esc(a), ParagraphStyle("QA", parent=body, fontSize=8.5, leading=12, textColor=slate))]
        ]
        q_tbl = Table(q_box, colWidths=[17.4 * cm])
        q_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), gray_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, gray_border),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, blue),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(q_tbl)
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 6))

    # ==========================================
    # SECTION 6: LIVE COLLEGE DEMO STEP-BY-STEP
    # ==========================================
    story.append(Paragraph("6. Step-by-Step Live Demonstration Checklist", h1))
    story.append(Paragraph("Follow this 3-minute sequence when presenting live:", body))
    story.append(Spacer(1, 3))
    
    demo_steps = [
        ("Step 1: Show the Repository", "Open the GitHub repo (e.g. CampusThrift) in the browser. Show the examiners the raw, messy commits to illustrate the problem."),
        ("Step 2: Trigger the Command", "Switch to PowerShell and run: <code>git2report --repo https://github.com/Rishav154/CampusThrift--An-Marketplace-for-University-Students --since 2026-07-01 --llm</code>"),
        ("Step 3: Point Out the Pipeline", "Show the terminal progress: Step 1 (Extract) -> Step 2 (Filter noise) -> Step 3 (Clustering) -> Step 4 (Metrics) -> Step 5-6 (AI Summaries) -> Step 7 (PDF)."),
        ("Step 4: Open report.pdf", "Open the generated <code>report.pdf</code> and highlight: (1) Executive TL;DR box, (2) Net Churn KPI (+14/-24), (3) Tech Stack breakdown, (4) Contributor Leaderboard, (5) Categorized commit badges with evidence hashes."),
    ]
    for d_step, d_text in demo_steps:
        story.append(Paragraph(f"<b>{d_step}</b>: {d_text}", bullet))

    # Running header & footer
    def add_page_decorations(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#64748B"))
        if d.page > 1:
            canvas.drawString(1.8 * cm, A4[1] - 1.2 * cm, "Git2Report — College Presentation & Operation Guide")
            canvas.drawRightString(A4[0] - 1.8 * cm, A4[1] - 1.2 * cm, "Confidential / Project Defense")
            canvas.setStrokeColor(gray_border)
            canvas.setLineWidth(0.5)
            canvas.line(1.8 * cm, A4[1] - 1.35 * cm, A4[0] - 1.8 * cm, A4[1] - 1.35 * cm)

        canvas.drawString(1.8 * cm, 1.1 * cm, "Git2Report | Computer Science Final Project Manual")
        canvas.drawRightString(A4[0] - 1.8 * cm, 1.1 * cm, f"Page {d.page}")
        canvas.setStrokeColor(gray_border)
        canvas.setLineWidth(0.5)
        canvas.line(1.8 * cm, 1.3 * cm, A4[0] - 1.8 * cm, 1.3 * cm)
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
    print(f"Generated guide PDF at: {output_path}")


if __name__ == "__main__":
    out = Path("college_project_guide.pdf")
    make_guide_pdf(out)
