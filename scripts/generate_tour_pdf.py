from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "subtracker-beginner-field-guide.pdf"

INK = colors.HexColor("#17251e")
GREEN = colors.HexColor("#195c43")
LIME = colors.HexColor("#d8ec99")
GOLD = colors.HexColor("#efbb62")
PAPER = colors.HexColor("#f4f1e9")
CARD = colors.HexColor("#fffdf8")
MUTED = colors.HexColor("#617067")
LINE = colors.HexColor("#d9d9cb")


def register_fonts() -> tuple[str, str, str]:
    windows_fonts = Path("C:/Windows/Fonts")
    candidates = {
        "sans": windows_fonts / "arial.ttf",
        "sans_bold": windows_fonts / "arialbd.ttf",
        "serif": windows_fonts / "georgia.ttf",
    }
    if all(path.exists() for path in candidates.values()):
        pdfmetrics.registerFont(TTFont("GuideSans", str(candidates["sans"])))
        pdfmetrics.registerFont(TTFont("GuideSansBold", str(candidates["sans_bold"])))
        pdfmetrics.registerFont(TTFont("GuideSerif", str(candidates["serif"])))
        return "GuideSans", "GuideSansBold", "GuideSerif"
    return "Helvetica", "Helvetica-Bold", "Times-Roman"


SANS, BOLD, SERIF = register_fonts()


class GuideDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            title="SubTracker Beginner Field Guide",
            author="SubTracker Team",
        )
        content_frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="content",
        )
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=content_frame, onPage=draw_cover_background),
                PageTemplate(id="body", frames=content_frame, onPage=draw_body_page),
            ]
        )


def draw_cover_background(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(LIME)
    canvas.circle(width - 28 * mm, height - 31 * mm, 23 * mm, fill=1, stroke=0)
    canvas.setFillColor(GREEN)
    canvas.rect(0, 0, 9 * mm, height, fill=1, stroke=0)
    canvas.restoreState()


def draw_body_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont(SANS, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "SUBTRACKER BEGINNER FIELD GUIDE")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"{doc.page}")
    canvas.restoreState()


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverKicker", fontName=BOLD, fontSize=10, leading=13, textColor=GREEN, spaceAfter=16, tracking=1.5))
styles.add(ParagraphStyle(name="CoverTitle", fontName=BOLD, fontSize=35, leading=38, textColor=INK, spaceAfter=16))
styles.add(ParagraphStyle(name="CoverItalic", fontName=SERIF, fontSize=29, leading=34, textColor=GREEN, spaceAfter=20))
styles.add(ParagraphStyle(name="CoverBody", fontName=SANS, fontSize=13, leading=20, textColor=MUTED, spaceAfter=14))
styles.add(ParagraphStyle(name="H1Guide", fontName=BOLD, fontSize=25, leading=29, textColor=INK, spaceBefore=4, spaceAfter=12))
styles.add(ParagraphStyle(name="H2Guide", fontName=BOLD, fontSize=15, leading=19, textColor=INK, spaceBefore=11, spaceAfter=6))
styles.add(ParagraphStyle(name="Kicker", fontName=BOLD, fontSize=8, leading=11, textColor=GREEN, tracking=1.2, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyGuide", fontName=SANS, fontSize=10, leading=15, textColor=INK, spaceAfter=7))
styles.add(ParagraphStyle(name="Muted", fontName=SANS, fontSize=9, leading=14, textColor=MUTED, spaceAfter=6))
styles.add(ParagraphStyle(name="FaqQ", fontName=BOLD, fontSize=11, leading=14, textColor=INK, spaceAfter=4))
styles.add(ParagraphStyle(name="FaqA", fontName=SANS, fontSize=9.2, leading=13.5, textColor=MUTED, spaceAfter=0))
styles.add(ParagraphStyle(name="GuideCode", fontName="Courier", fontSize=8.5, leading=12, textColor=GREEN))
styles.add(ParagraphStyle(name="Center", fontName=SANS, fontSize=10, leading=14, textColor=INK, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="StepLabel", fontName=BOLD, fontSize=13, leading=16, textColor=LIME))


def p(text: str, style: str = "BodyGuide") -> Paragraph:
    return Paragraph(text, styles[style])


def section_header(number: str, kicker: str, title: str) -> list:
    return [
        p(f"{number}  {kicker.upper()}", "Kicker"),
        p(title, "H1Guide"),
        Spacer(1, 2 * mm),
    ]


def callout(title: str, body: str, background=CARD, accent=GREEN) -> Table:
    table = Table(
        [[p(title, "H2Guide"), p(body, "BodyGuide")]],
        colWidths=[42 * mm, 118 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("LINEBEFORE", (0, 0), (0, -1), 4, accent),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def faq(question: str, answer: str, label: str) -> KeepTogether:
    box = Table(
        [[p(label.upper(), "Kicker"), p(question, "FaqQ")], ["", p(answer, "FaqA")]],
        colWidths=[27 * mm, 133 * mm],
        hAlign="LEFT",
    )
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD),
                ("BOX", (0, 0), (-1, -1), 0.45, LINE),
                ("SPAN", (0, 0), (0, 1)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return KeepTogether([box, Spacer(1, 3 * mm)])


def build_story() -> list:
    story = [
        Spacer(1, 27 * mm),
        p("BEGINNER ONBOARDING / SOLO BUILD FIRST", "CoverKicker"),
        p("SubTracker", "CoverTitle"),
        p("Beginner Field Guide", "CoverItalic"),
        p("Where to start, what to build, what to ignore, and how to get unstuck without waiting for someone else.", "CoverBody"),
        Spacer(1, 18 * mm),
        callout("First destination", "<font name='Courier'>docs/learning/solo-prototype.md</font><br/><br/>Not backend/. Not Docker. Not the whole application.", background=colors.white, accent=GOLD),
        Spacer(1, 22 * mm),
        p("ONE RULE", "CoverKicker"),
        p("Build one small AI loop and be able to explain every part of it.", "CoverBody"),
        NextPageTemplate("body"),
        PageBreak(),
    ]

    story += section_header("01", "Where to start", "Your first 30 minutes")
    story += [
        callout("1. Read", "Open <font name='Courier'>README.md</font>, then read <font name='Courier'>docs/learning/solo-prototype.md</font> from top to bottom."),
        Spacer(1, 4 * mm),
        callout("2. Restate", "In your own words, explain the input, allowed recommendations, required evidence, uncertainty, and savings output."),
        Spacer(1, 4 * mm),
        callout("3. Sketch", "Draw this loop: structured input -> Python tools -> model -> Pydantic validation -> evaluation result."),
        Spacer(1, 4 * mm),
        callout("4. Begin", "Create the smallest runnable interface: CLI, notebook, or one small FastAPI endpoint."),
        Spacer(1, 6 * mm),
        p("THE ASSIGNMENT IN ONE SENTENCE", "Kicker"),
        p("Given subscription and usage evidence, return a validated keep, downgrade, cancel, or review recommendation with evidence, uncertainty, confidence, and deterministic savings.", "H2Guide"),
        Spacer(1, 4 * mm),
        callout("Permission to ignore", "Docker, PostgreSQL, Redis, authentication, a polished frontend, bank connections, cancellation automation, and the complete shared API.", background=colors.HexColor("#efe2c7"), accent=GOLD),
        PageBreak(),
    ]

    story += section_header("02", "Solo route", "Five steps to a useful prototype")
    rows = []
    steps = [
        ("01 Read", "Understand the shared task and cases."),
        ("02 Model", "Define Pydantic input and output schemas."),
        ("03 Build", "Add a model call and deterministic tools."),
        ("04 Break", "Test missing data, bad output, and hostile text."),
        ("05 Explain", "Record decisions, failures, scores, and questions."),
    ]
    for label, body in steps:
        rows.append([p(label, "StepLabel"), p(body, "BodyGuide")])
    table = Table(rows, colWidths=[42 * mm, 118 * mm])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.45, LINE), ("BACKGROUND", (0, 0), (0, -1), INK), ("TEXTCOLOR", (0, 0), (0, -1), LIME), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9)]))
    story += [table, Spacer(1, 8 * mm)]
    story += [
        p("REQUIRED INPUT", "Kicker"),
        p("Subscription and provider; price, currency, and billing period; recent charges; usage events or an explicit unknown state; renewal date; user preferences; plan alternatives; analysis date."),
        p("REQUIRED OUTPUT", "Kicker"),
        p("Action; reason; evidence with references; uncertainties; confidence; monthly and annual savings; a follow-up question when needed; approval-required flag; schema, prompt, and model references."),
        p("REQUIRED PYTHON TOOLS", "Kicker"),
        p("<b>calculate_savings</b> computes money and billing periods. <b>summarize_usage</b> computes recency and frequency or reports unknown. The model explains verified numbers; it does not invent them."),
        PageBreak(),
    ]

    story += section_header("03", "Repository compass", "Read by phase, not by folder size")
    compass = [
        [p("READ NOW", "Kicker"), p("docs/learning/solo-prototype.md", "GuideCode"), p("Your exact task, cases, tools, and completion criteria.")],
        [p("READ NEXT", "Kicker"), p("docs/learning/comparison-and-convergence.md", "GuideCode"), p("How all seven experiments will be compared and combined.")],
        [p("READ LATER", "Kicker"), p("docs/product/vision-and-scope.md", "GuideCode"), p("The product problem, MVP boundary, and end-state user journey.")],
        [p("READ LATER", "Kicker"), p("docs/architecture/", "GuideCode"), p("The shared FastAPI, data, API, and AI-system design.")],
        [p("READ LATER", "Kicker"), p("docs/platform/", "GuideCode"), p("Docker, development, security, testing, and operations.")],
        [p("IGNORE FOR SOLO", "Kicker"), p("backend/ and compose.yaml", "GuideCode"), p("Shared-system foundation. It is not your first assignment.")],
    ]
    compass_table = Table(compass, colWidths=[31 * mm, 62 * mm, 67 * mm], repeatRows=0)
    compass_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, 0), (-1, -1), CARD), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story += [compass_table, Spacer(1, 9 * mm)]
    story += [
        p("WHY EVERYONE BUILDS THE SAME THING", "Kicker"),
        p("Every participant must personally practice prompting, schemas, tools, grounding, failures, and evaluation. Shared cases make the experiments comparable. The final design is chosen from evidence, not polish."),
        callout("The full journey", "Phase 0: agree on the same task<br/>Phase 1: seven solo prototypes<br/>Phase 2: compare evidence and failures<br/>Phase 3: build one shared production-structured system", background=LIME),
        PageBreak(),
    ]

    story += section_header("04", "FAQ", "Starting and scope")
    starting = [
        ("Where do I start?", "Read README.md, then docs/learning/solo-prototype.md. Do not begin in backend/.", "Starting"),
        ("Do I need to understand the whole repository?", "No. Learn the solo task, its input/output, tools, and cases. Architecture and platform documents are for later phases.", "Starting"),
        ("Am I building the entire app?", "No. Build only a narrow recommendation loop. No authentication, full frontend, live bank data, or cancellation automation.", "Scope"),
        ("Can I use a CLI or notebook?", "Yes. A CLI, notebook, or one small FastAPI endpoint is enough. AI-system quality matters more than polish.", "Scope"),
        ("Do I need Docker or PostgreSQL?", "No. Those are shared-system tools. Your solo time should focus on the AI loop.", "Tools"),
        ("Are we using pip?", "No. Use uv for Python dependency management and reproducible commands.", "Tools"),
    ]
    for q, a, label in starting:
        story.append(faq(q, a, label))
    story.append(PageBreak())

    story += section_header("05", "FAQ", "AI concepts in plain language")
    concepts = [
        ("What is structured output?", "A predictable data object validated against a schema, not an uncontrolled paragraph. Define it with Pydantic and reject invalid results.", "Concept"),
        ("What is tool calling?", "The model requests a named Python function for a task such as savings calculation. The program runs the tool and returns the verified result.", "Concept"),
        ("What is grounding?", "Every factual claim should be supported by the supplied evidence. The model cannot claim the user stopped using a service when usage is unknown.", "Concept"),
        ("What is an evaluation?", "A repeatable test case with expected allowed actions, required evidence, forbidden claims, savings, and failure severity.", "Concept"),
        ("Why not let the model calculate savings?", "Language models are not the source of truth for arithmetic or billing logic. Tested Python code calculates; the model interprets and explains.", "Design"),
        ("What if usage is missing?", "Unknown is not zero. Lower confidence, ask a follow-up question, or return review unless other strong evidence exists.", "Safety"),
    ]
    for q, a, label in concepts:
        story.append(faq(q, a, label))
    story.append(PageBreak())

    story += section_header("06", "FAQ", "Failure and troubleshooting")
    failures = [
        ("The model returned invalid JSON. Now what?", "Capture the failure, validate the response, retry only within a clear limit, and fail safely when the limit is reached. Record what happened.", "Failure"),
        ("The model calculated the wrong savings.", "Move the calculation into calculate_savings and pass the verified result into the reasoning context.", "Failure"),
        ("The model says cancel when usage is unknown.", "Treat this as a grounding and uncertainty failure. Require acknowledgement of missing data, a question, lower confidence, or review.", "Failure"),
        ("My answer sounds good. Is that enough?", "No. Run the shared normal and adversarial cases. Check the schema, facts, calculations, uncertainty, safety, repeatability, latency, and cost.", "Quality"),
        ("How do I know I am done?", "Your prototype handles shared cases and malformed output, uses tested tools, records failures, and you can explain every important design choice.", "Done"),
        ("Should I hide failed cases in my presentation?", "No. Failures are one of the most valuable results. They reveal the checks and architecture the shared system needs.", "Learning"),
    ]
    for q, a, label in failures:
        story.append(faq(q, a, label))
    story.append(PageBreak())

    story += section_header("07", "Team process", "What happens after the solo build")
    story += [
        p("Every prototype runs the same evaluation cases. The team compares recommendation correctness, grounding, savings accuracy, uncertainty, schema reliability, safety, explanation quality, and maintainability."),
        Spacer(1, 3 * mm),
        callout("Not a winner-takes-all contest", "The shared system may use one prototype's schema, another's tools, a third's failure handling, and evaluation ideas from several people.", background=LIME),
        Spacer(1, 6 * mm),
        p("COMPARISON QUESTIONS", "Kicker"),
        p("- Which schema represented evidence and uncertainty best?<br/>- Which prompt generalized instead of memorizing examples?<br/>- Which tasks should never have been delegated to the model?<br/>- Which failures could cause the most harm?<br/>- Were confidence values meaningful?<br/>- Which design will be easiest to test and improve?"),
        Spacer(1, 5 * mm),
        p("PHASE 2 OUTPUT", "Kicker"),
        p("One domain vocabulary, canonical input contract, versioned recommendation schema, selected Python tools, baseline prompt strategy, evaluation dataset, architecture decisions, and shared-system backlog."),
        Spacer(1, 6 * mm),
        callout("Exit rule", "Shared product features begin only when the team can defend the shared design using prototype evidence.", background=colors.HexColor("#efe2c7"), accent=GOLD),
        PageBreak(),
    ]

    story += section_header("08", "Get help well", "A question someone can answer quickly")
    story += [
        p("Before asking, search the interactive FAQ, reread the relevant solo-build section, and reduce the problem to the smallest failing case."),
        Spacer(1, 4 * mm),
        callout("Help template", "<font name='Courier'>Case/input: ...<br/>Expected behavior: ...<br/>Actual result/error: ...<br/>Smallest relevant code or prompt: ...<br/>What I already tried: ...<br/>My current theory: ...</font>", background=CARD, accent=GREEN),
        Spacer(1, 7 * mm),
        p("NEVER SHARE", "Kicker"),
        p("API keys, passwords, access tokens, real financial data, or another person's private information."),
        Spacer(1, 7 * mm),
        p("BEFORE YOU SAY 'I AM STUCK'", "Kicker"),
        p("1. Read the complete error message.<br/>2. Identify which step failed: input, tool, model call, validation, or evaluation.<br/>3. Run the smallest case again.<br/>4. Print or log the structured values safely.<br/>5. Write what you expected and why.<br/>6. Ask with the template above."),
        Spacer(1, 12 * mm),
        callout("Remember", "Start small. Make failures visible. Be able to explain your system.", background=LIME),
    ]
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    GuideDocTemplate(str(OUTPUT)).build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()
