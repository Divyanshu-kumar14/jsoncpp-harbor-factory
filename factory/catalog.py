"""Declarative catalogue of mined jsoncpp tasks.

Each entry must describe a capability that is *absent* from the pinned baseline.
The generator enforces that with `absent_markers`; that gate is why this factory
does not emit patches that are already upstream.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    slug: str
    task_name: str
    title: str
    description: str
    difficulty: str
    category: str
    feature: str
    tags: list[str]
    expert_min: float
    junior_min: float
    hidden_tests: list[str]
    absent_markers: list[tuple[str, str]]
    present_markers: list[tuple[str, str]]
    verifier_timeout: float = 300.0
    agent_timeout: float = 900.0
    build_timeout: float = 900.0
    author: str = "Innodata AI Hackathon Team"
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def directory(self) -> str:
        return f"{self.task_id}-{self.slug}"


TASKS: list[TaskSpec] = [
    TaskSpec(
        task_id="task-001",
        slug="strict-utf8",
        task_name="innodata/jsoncpp-strict-utf8",
        title="Strict UTF-8 validation for jsoncpp string parsing",
        description=(
            "Add a CharReaderBuilder validateUTF8 setting that rejects malformed "
            "UTF-8 string bytes per RFC 8259, with line/column diagnostics."
        ),
        difficulty="easy",
        category="cpp-json-reader",
        feature="CharReaderBuilder.validateUTF8",
        tags=["jsoncpp", "reader", "utf8", "rfc8259", "security"],
        expert_min=20.0,
        junior_min=40.0,
        hidden_tests=["test_strict_utf8.cpp"],
        absent_markers=[
            ("src/lib_json/json_reader.cpp", "validateUTF8"),
            ("include/json/reader.h", "validateUTF8"),
        ],
        present_markers=[
            ("src/lib_json/json_reader.cpp", "validateUTF8"),
            ("src/lib_json/json_reader.cpp", "Invalid UTF-8 sequence in string"),
            ("include/json/reader.h", "validateUTF8"),
        ],
        metadata={"bug_class": "input-validation", "rfc": "8259"},
    ),
    TaskSpec(
        task_id="task-002",
        slug="json-pointer",
        task_name="innodata/jsoncpp-json-pointer",
        title="RFC 6901 JSON Pointer lookup for Json::Value",
        description=(
            "Add const and mutable Value::findPointer methods implementing "
            "RFC 6901 tokens, escapes, and array index grammar."
        ),
        difficulty="medium",
        category="cpp-json-dom",
        feature="Value.findPointer",
        tags=["jsoncpp", "dom", "json-pointer", "rfc6901", "api"],
        expert_min=30.0,
        junior_min=60.0,
        hidden_tests=["test_json_pointer.cpp"],
        absent_markers=[
            ("include/json/value.h", "findPointer"),
            ("src/lib_json/json_value.cpp", "findPointer"),
        ],
        present_markers=[
            ("include/json/value.h", "findPointer"),
            ("src/lib_json/json_value.cpp", "decodePointerToken"),
            ("src/lib_json/json_value.cpp", "JSON Pointer must be empty"),
        ],
        metadata={"rfc": "6901", "api_surface": "DOM"},
    ),
    TaskSpec(
        task_id="task-003",
        slug="roundtrip-precision",
        task_name="innodata/jsoncpp-roundtrip-precision",
        title="Shortest round-trip double formatting for jsoncpp",
        description=(
            "Add StreamWriterBuilder precisionMode=roundTrip so doubles serialize "
            "as the shortest string that parses back to the identical value."
        ),
        difficulty="hard",
        category="cpp-json-writer",
        feature="StreamWriterBuilder.precisionMode",
        tags=["jsoncpp", "writer", "floating-point", "round-trip", "ieee754"],
        expert_min=45.0,
        junior_min=90.0,
        hidden_tests=["test_precision_mode.cpp"],
        absent_markers=[
            ("src/lib_json/json_writer.cpp", "precisionMode"),
            ("include/json/writer.h", "precisionMode"),
        ],
        present_markers=[
            ("src/lib_json/json_writer.cpp", "precisionMode"),
            ("src/lib_json/json_writer.cpp", "roundTrip"),
            ("include/json/value.h", "roundTrip"),
            ("include/json/writer.h", "precisionMode"),
        ],
        metadata={"issue": "420", "numeric": "binary64"},
    ),
]


def select(task_ids: list[str] | None = None, limit: int | None = None) -> list[TaskSpec]:
    tasks = TASKS
    if task_ids:
        wanted = {task_id.split("-")[-1] for task_id in task_ids}
        tasks = [
            task
            for task in tasks
            if task.task_id in task_ids
            or task.slug in task_ids
            or task.task_id.split("-")[-1] in wanted
        ]
        if not tasks:
            raise SystemExit(f"no catalogue entries match {task_ids!r}")
    if limit is not None:
        if limit > len(TASKS):
            print(
                f"note: --n {limit} requested but the catalogue has "
                f"{len(TASKS)} verified tasks; generating all {len(TASKS)}"
            )
        tasks = tasks[:limit]
    return tasks
