"""Fill the Innodata IDEA SUBMISSION deck with this project's real results.

The template is a Google-Slides export: full-bleed PNG backgrounds plus text
boxes. Content slides 2-10 have black backgrounds, so body text is set light.
Diagrams are rendered with Graphviz in the same dark palette; the CLI panel is
drawn with Pillow.

Run:
    uv run --with python-pptx --with pillow --no-project python factory/deck.py \
        --template "/home/rtx/Downloads/Innodata _ IDEA SUBMISSION.pptx" \
        --output submission/Innodata_IDEA_SUBMISSION_jsoncpp.pptx
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt

WHITE = RGBColor(0xF3, 0xF5, 0xF8)
BODY = RGBColor(0xD5, 0xDB, 0xE3)
MUTED = RGBColor(0x98, 0xA2, 0xAE)
DARK_BODY = RGBColor(0x36, 0x3B, 0x43)
DARK_MUTED = RGBColor(0x6A, 0x72, 0x7D)
ORANGE = RGBColor(0xFF, 0x6B, 0x1A)
ACCENT = RGBColor(0xD9, 0x4A, 0x0F)
DARK = RGBColor(0x1F, 0x1F, 0x1F)
INK = RGBColor(0x20, 0x27, 0x29)

TITLE_FONT = "League Spartan Medium"
BODY_FONT = "League Spartan"
MONO_FONT = "/usr/share/fonts/noto/NotoSansMono-Regular.ttf"

PROCESS_DOT = """
digraph process {
  graph [rankdir=TB, bgcolor="transparent", pad=0.10, nodesep=0.30, ranksep=0.42];
  node [shape=box, style="rounded,filled", fillcolor="#F7F8FA", color="#202729",
        fontcolor="#1F1F1F", fontname="Helvetica", fontsize=16,
        margin="0.22,0.13", penwidth=1.4];
  edge [color="#D9480F", penwidth=1.8, arrowsize=0.85];
  { rank=same; baseline; miner; generator; }
  { rank=same; packager; validator; lint; }
  baseline  [label="Pinned baseline\\njsoncpp 93acc7b"];
  miner     [label="1 · miner\\nast-grep + issues"];
  generator [label="2 · generator\\nnovelty + preflight"];
  lint      [label="3 · harbor lint\\nfail closed"];
  validator [label="4 · validator\\noracle 1 / no-op 0"];
  packager  [label="5 · packager\\nzip + evidence"];
  baseline -> miner -> generator;
  generator -> lint;
  lint -> validator;
  validator -> packager;
}
"""

ARCH_DOT = """
digraph arch {
  graph [rankdir=LR, bgcolor="transparent", pad=0.10, nodesep=0.40, ranksep=0.55];
  node [shape=box, style="rounded,filled", fillcolor="#F7F8FA", color="#202729",
        fontcolor="#1F1F1F", fontname="Helvetica", fontsize=18,
        margin="0.24,0.16", penwidth=1.6];
  edge [color="#D9480F", penwidth=1.8, arrowsize=0.85, fontcolor="#4A525C",
        fontname="Helvetica", fontsize=14];

  source  [label="AGENT\\n/app/jsoncpp\\nbaseline + agent edits",
           fillcolor="#EAF2FF", color="#2F7FE0", fontcolor="#12345A"];
  artifact [shape=note, label="artifact\\n/app/jsoncpp",
            fillcolor="#FFF4E5", color="#D9480F", fontcolor="#5A2B00"];
  verifier [label="SEPARATE VERIFIER\\nrebuild + run hidden tests",
            fillcolor="#EAF7EF", color="#1F9254", fontcolor="#0F3D24"];
  reward  [label="reward.txt\\n1 or 0",
           fillcolor="#FFF4E5", color="#D9480F", fontcolor="#5A2B00"];

  source -> artifact [label="collect"];
  artifact -> verifier [label="restore"];
  verifier -> reward [label="pass / fail"];
}
"""

TERMINAL_LINES = [
    ("cmd", "$ ./generate.sh --repo jsoncpp --n 3"),
    ("stage", "== harbor 0.25.0 / docker 29.10.1 =="),
    ("stage", "== miner =="),
    ("out", "miner: 579 functions across 12 files using ast-grep"),
    ("out", "miner: 31 matching upstream issues"),
    ("stage", "== generator =="),
    ("out", "generate: task-001 (easy) CharReaderBuilder.validateUTF8"),
    ("out", "generate: task-002 (medium) Value.findPointer"),
    ("out", "generate: task-003 (hard) StreamWriterBuilder.precisionMode"),
    ("stage", "== lint =="),
    ("good", "packager: harbor lint exit=0 findings=0"),
    ("stage", "== validator (oracle expects 1, no-op expects 0) =="),
    ("good", "task-001: PASS (positive=1.0, negative=0.0)"),
    ("good", "task-002: PASS (positive=1.0, negative=0.0)"),
    ("good", "task-003: PASS (positive=1.0, negative=0.0)"),
    ("stage", "== packager =="),
    ("good", "packager: wrote submission/jsoncpp-harbor-tasks.zip (46 entries)"),
]


def style(run, *, size: float, color: RGBColor, font: str = BODY_FONT, bold=False):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return run


def add_line(tf, text, *, first=False, size=13, color=DARK_BODY, font=BODY_FONT,
             bold=False, space_before=0, space_after=5, bullet=None):
    paragraph = tf.paragraphs[0] if first else tf.add_paragraph()
    paragraph.space_before = Pt(space_before)
    paragraph.space_after = Pt(space_after)
    paragraph.line_spacing = 1.05
    if bullet:
        marker = paragraph.add_run()
        marker.text = bullet + "  "
        style(marker, size=size, color=ACCENT, font=font, bold=True)
    run = paragraph.add_run()
    run.text = text
    style(run, size=size, color=color, font=font, bold=bold)
    return paragraph


def kicker(tf, text, *, first=True):
    paragraph = tf.paragraphs[0] if first else tf.add_paragraph()
    paragraph.space_before = Pt(0)
    paragraph.space_after = Pt(2)
    run = paragraph.add_run()
    run.text = text
    style(run, size=11, color=ACCENT, font=TITLE_FONT, bold=True)
    rpr = run._r.get_or_add_rPr()
    rpr.set("spc", "160")
    return paragraph


def clear(tf, *, autosize=MSO_AUTO_SIZE.NONE):
    tf.clear()
    tf.word_wrap = True
    tf.auto_size = autosize


def set_box(shape, left=None, top=None, width=None, height=None):
    if left is not None:
        shape.left = Inches(left)
    if top is not None:
        shape.top = Inches(top)
    if width is not None:
        shape.width = Inches(width)
    if height is not None:
        shape.height = Inches(height)


def note_box(slide, left, top, width, height, lines, *, size=12, color=DARK_BODY):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    frame = box.text_frame
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    for index, line in enumerate(lines):
        add_line(frame, line, first=(index == 0), size=size, color=color,
                 bullet="•", space_after=5)
    return box


def caption(slide, text, top, *, left=0.55, width=8.9, size=10.5):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(0.3))
    frame = box.text_frame
    frame.word_wrap = True
    frame.auto_size = MSO_AUTO_SIZE.NONE
    add_line(frame, text, first=True, size=size, color=DARK_MUTED, space_after=0)
    return box


def render_dot(source: str, out_png: Path, dpi: int = 220) -> None:
    dot = out_png.with_suffix(".dot")
    dot.write_text(source)
    subprocess.run(
        ["dot", "-Tpng", f"-Gdpi={dpi}", str(dot), "-o", str(out_png)],
        check=True,
    )


def terminal_png(out_png: Path) -> None:
    width, height = 1800, 760
    image = Image.new("RGB", (width, height), "#0B0D10")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([0, 0, width - 1, height - 1], radius=22, outline="#2A3038", width=3)
    draw.rounded_rectangle([0, 0, width - 1, 54], radius=22, fill="#15181C")
    draw.rectangle([0, 32, width - 1, 54], fill="#15181C")
    for index, colour in enumerate(["#FF5F57", "#FEBC2E", "#28C840"]):
        x = 28 + index * 30
        draw.ellipse([x, 19, x + 15, 34], fill=colour)
    draw.text((140, 17), "jsoncpp-harbor-factory  ·  zsh", fill="#8B95A3", font=ImageFont.truetype(MONO_FONT, 20))

    font = ImageFont.truetype(MONO_FONT, 25)
    colours = {"cmd": "#F5F7FA", "stage": "#FF8A3D", "out": "#C8D0DA", "good": "#3DDC84"}
    y = 82
    for kind, line in TERMINAL_LINES:
        draw.text((38, y), line, fill=colours[kind], font=font)
        y += 39
    image.save(out_png)


def fill_slide1(slide) -> None:
    boxes = [shape for shape in slide.shapes if shape.has_text_frame]
    by_text = {shape.text_frame.text.strip(): shape for shape in boxes}

    team = by_text["Team Name :"]
    para = team.text_frame.paragraphs[0]
    para.runs[0].text = "Team Name :  "
    style(para.runs[0], size=17, color=INK, font=TITLE_FONT, bold=True)
    value = para.add_run()
    value.text = "jsoncpp Task Factory"
    style(value, size=16, color=INK)

    leader = by_text["Team Leader Name :"]
    para = leader.text_frame.paragraphs[0]
    para.runs[0].text = "Team Leader Name :  "
    style(para.runs[0], size=17, color=INK, font=TITLE_FONT, bold=True)
    value = para.add_run()
    value.text = "Divyanshu"
    style(value, size=16, color=INK)

    problem = by_text["Problem Statement :"]
    frame = problem.text_frame
    frame.auto_size = MSO_AUTO_SIZE.NONE
    frame.word_wrap = True
    frame.paragraphs[0].runs[0].text = "Problem Statement :"
    style(frame.paragraphs[0].runs[0], size=17, color=INK, font=TITLE_FONT, bold=True)
    add_line(
        frame,
        "AI coding benchmarks are expensive to author and easy to leak. This factory "
        "turns a pinned C++ repository into non-trivial, containerized Harbor tasks — "
        "and proves every one with a 0/1 gate.",
        first=False, size=10.5, color=INK, space_before=1, space_after=0,
    )
    set_box(problem, top=4.42, height=0.95)


def content_slide(slide, kicker_text: str, headline: str, *, title_top=0.78,
                  height=3.9, headline_size=24):
    boxes = [s for s in slide.shapes if s.has_text_frame]
    shape = max(boxes, key=lambda item: item.width * item.height)
    clear(shape.text_frame)
    kicker(shape.text_frame, kicker_text)
    add_line(shape.text_frame, headline, size=headline_size, color=INK,
             font=TITLE_FONT, space_before=2, space_after=10)
    set_box(shape, left=0.34, top=title_top, width=9.32, height=height)
    shape.text_frame.paragraphs[0].alignment = PP_ALIGN.LEFT
    return shape.text_frame


def build(template: Path, output: Path, work: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    process_png = work / "process.png"
    arch_png = work / "architecture.png"
    term_png = work / "terminal.png"
    render_dot(PROCESS_DOT, process_png)
    render_dot(ARCH_DOT, arch_png)
    terminal_png(term_png)

    prs = Presentation(str(template))
    slides = list(prs.slides)

    fill_slide1(slides[0])

    # Remove the template's leftover "Brief about the Idea" placeholder box on slide 2.
    for shape in list(slides[1].shapes):
        if shape.has_text_frame and "Brief about the Idea" in shape.text_frame.text:
            element = shape._element
            element.getparent().remove(element)

    # 02 — the idea
    tf = content_slide(slides[1], "01 · THE IDEA",
                       "A factory that proves its own tasks are non-trivial")
    add_line(tf, "Jsoncpp Harbor Task Factory converts open-source-parsers/jsoncpp at "
                 "commit 93acc7b into independent Harbor v0.25.0 task packages. One "
                 "command runs mining, generation, lint, validation and packaging.",
             size=13, color=DARK_BODY)
    add_line(tf, "The generator refuses any capability already present at the baseline, "
                 "then applies the reference patch, builds jsoncpp and runs the hidden "
                 "test before a package is allowed to exist.", size=13, color=DARK_BODY)
    add_line(tf, "Three tasks cover the reader, DOM and writer. All six gate runs "
                 "returned 1 with the reference solution and 0 with a no-op solution.",
             size=13, color=DARK_BODY)

    # 03 — opportunity
    tf = content_slide(slides[2], "02 · OPPORTUNITY",
                       "Benchmarks should be generated, not hand-written")
    for heading, body in [
        ("How is it different?",
         "A novelty gate blocks tasks that upstream already solved. Every package is "
         "compiled and tested before it ships, so “already implemented” and “does not "
         "build” cannot masquerade as benchmark tasks."),
        ("How does it solve the problem?",
         "Pinned baseline → mined gap → reference patch → isolated verifier → "
         "two-sided reward. Hidden tests live only in the verifier image and grade a "
         "rebuild of the agent's source."),
        ("USP",
         "Non-triviality is enforced mechanically, and every reward is backed by a raw "
         "1/0 file. The same pipeline reproduces all three tasks from one command."),
    ]:
        add_line(tf, heading, size=14, color=INK, font=TITLE_FONT,
                 space_before=8, space_after=2)
        add_line(tf, body, size=12.5, color=DARK_BODY, space_after=3)

    # 04 — features
    tf = content_slide(slides[3], "03 · FEATURES", "Six stages, each fail-closed")
    for item in [
        "ast-grep function map: 579 definitions across 12 files, plus 31 upstream issues from gh.",
        "Novelty gate: absent-marker checks reject features that already exist at 93acc7b.",
        "Preflight: patch, symbol check, CMake build and hidden test before packaging.",
        "Harbor 0.25 packaging: schema 1.4, separate verifier, digest-pinned Ubuntu 24.04.",
        "Artifact transfer: /app/jsoncpp crosses the boundary; /app/build never does.",
        "Two-sided validation: oracle must score 1, a no-op solve.sh must score 0.",
        "Packager: harbor lint must report zero findings, then emits the submission zip.",
    ]:
        add_line(tf, item, size=12.5, color=DARK_BODY, bullet="•", space_after=4)

    # 05 — process
    content_slide(slides[4], "04 · PROCESS", "Mine → generate → lint → validate → package",
                  height=0.95)
    slides[4].shapes.add_picture(str(process_png), Inches(0.55), Inches(1.82), width=Inches(8.9))
    caption(slides[4], "A failure at any stage stops the run; no package is produced.", 3.55)
    note_box(slides[4], 0.6, 3.92, 8.8, 1.5, [
        "Novelty gate: the capability must be absent at 93acc7b, or the task is refused.",
        "Preflight: the reference patch must compile and pass the hidden test before packaging.",
        "Validator: each task runs twice — with the reference solution (1) and a no-op (0).",
    ], size=12)

    # 06 — interface
    content_slide(slides[5], "05 · INTERFACE", "One command, every stage", height=0.95)
    slides[5].shapes.add_picture(str(term_png), Inches(1.3), Inches(1.72), width=Inches(7.4))
    caption(slides[5], "./generate.sh --repo jsoncpp --n 3 — the full reproduction path.",
            5.05, left=1.3, width=7.4)

    # 07 — architecture
    content_slide(slides[6], "06 · ARCHITECTURE", "Isolated grading by construction",
                  height=0.95)
    slides[6].shapes.add_picture(str(arch_png), Inches(0.55), Inches(1.9), width=Inches(8.9))
    caption(slides[6], "The verifier rebuilds the agent's source in a fresh container.", 2.98)
    note_box(slides[6], 0.6, 3.38, 8.8, 1.3, [
        "Only /app/jsoncpp crosses the boundary; /app/build is deliberately excluded.",
        "Hidden tests are baked into tests/Dockerfile and never enter the agent image.",
        "A tampered build directory cannot influence the reward — the verifier rebuilds.",
    ], size=12)
    callout = slides[6].shapes.add_textbox(Inches(0.6), Inches(4.7), Inches(8.8), Inches(0.4))
    callout.text_frame.word_wrap = True
    add_line(callout.text_frame, "Every reward is a raw 1 or 0 in /logs/verifier/reward.txt.",
             first=True, size=12.5, color=ACCENT, font=TITLE_FONT, space_after=0)

    # 08 — stack
    tf = content_slide(slides[7], "07 · STACK", "Small, open, reproducible")
    for item in [
        "Python 3 standard library — miner, generator, validator, packager.",
        "Harbor 0.25.0 exactly; task schema 1.4 with separate verifier.",
        "Docker 29 · Ubuntu 24.04 pinned by SHA-256 digest.",
        "GCC 13 · CMake · static libjsoncpp.a built in-image.",
        "ast-grep for typed function mining; gh CLI for issue context.",
        "Bash verifier that always writes /logs/verifier/reward.txt.",
        "No paid APIs, no runtime network, no credentials.",
    ]:
        add_line(tf, item, size=13, color=DARK_BODY, bullet="•", space_after=5)

    # 09 — cost
    tf = content_slide(slides[8], "08 · COST", "Near-zero marginal cost")
    for item in [
        "All components are open source: jsoncpp (MIT), Harbor, ast-grep, Docker.",
        "Full 3-task regeneration plus six Harbor trials: under 10 minutes on a 16-core laptop.",
        "Three 183 KB source snapshots; the submission zip is 567 KB.",
        "Adding a task costs one catalogue entry, one patch and one hidden test — not a new harness.",
    ]:
        add_line(tf, item, size=13, color=DARK_BODY, bullet="•", space_after=7)

    # 10 — deliverables
    tf = content_slide(slides[9], "09 · DELIVERABLES", "What the judges can run")
    for item in [
        "github.com/Divyanshu-kumar14/jsoncpp-harbor-factory — public, 75 files.",
        "tasks/task-001-strict-utf8 · task-002-json-pointer · task-003-roundtrip-precision.",
        "submission/jsoncpp-harbor-tasks.zip — 46 entries, canonical Harbor layout.",
        "evidence/rewards/*.txt — raw 1/0 files from all six trials.",
        "validation.log · evidence/lint.json · README.md · ARCHITECTURE.md.",
        "Verified: harbor lint 0 findings; positive 1.0, negative 0.0 on every task.",
    ]:
        add_line(tf, item, size=12.5, color=DARK_BODY, bullet="•", space_after=5)

    # Slide 11 is the template's branded closing slide; leave it untouched.

    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output))
    print(f"deck: wrote {output} ({output.stat().st_size / 1024:.0f} KB)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work", type=Path, default=Path(".work/deck"))
    args = parser.parse_args()
    if not args.template.is_file():
        raise SystemExit(f"template not found: {args.template}")
    build(args.template, args.output, args.work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
