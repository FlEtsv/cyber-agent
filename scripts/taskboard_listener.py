"""Watch TASKBOARD.md and report coordination changes.

This is intentionally read-only: it never edits the board and never starts
agent work by itself. It gives Claude, Codex, or Steve a small local monitor
for new objectives and approved tasks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


TASK_ID_RE = re.compile(r"^[BF]\d{3}$", re.IGNORECASE)
SECTION_RE = re.compile(r"^##\s+.*?([A-ZÁÉÍÓÚÑ ]+)\s*$", re.MULTILINE)
APPROVED_MARKERS = {"✅", "[x]", "x", "yes", "si", "sí", "approved", "aprobado"}


@dataclass(frozen=True)
class Task:
    task_id: str
    approved: bool
    description: str
    files: str
    agent: str
    priority: str


@dataclass(frozen=True)
class Snapshot:
    digest: str
    objective: str
    in_progress: str
    completed: str
    blocked: str
    tasks: list[Task]


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def section(text: str, name: str) -> str:
    matches = list(SECTION_RE.finditer(text))
    target = name.upper()
    for index, match in enumerate(matches):
        heading = " ".join(match.group(1).upper().split())
        if target in heading:
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            return text[start:end].strip()
    return ""


def strip_code_fence(value: str) -> str:
    value = value.strip()
    fenced = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)\n```", value, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    if value.startswith("```") and value.endswith("```"):
        lines = value.splitlines()
        return "\n".join(lines[1:-1]).strip()
    return value


def is_empty_marker(value: str) -> bool:
    compact = value.strip().lower()
    return not compact or "sin objetivo activo" in compact or "vacío" in compact or "vacio" in compact


def is_approved(value: str) -> bool:
    normalized = value.strip().lower()
    return any(marker in normalized for marker in APPROVED_MARKERS)


def parse_tasks(text: str) -> list[Task]:
    tasks: list[Task] = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw.startswith("|"):
            continue
        cells = [cell.strip() for cell in raw.strip("|").split("|")]
        if len(cells) < 6 or not TASK_ID_RE.match(cells[0]):
            continue
        tasks.append(
            Task(
                task_id=cells[0].upper(),
                approved=is_approved(cells[1]),
                description=cells[2],
                files=cells[3],
                agent=cells[4].lower(),
                priority=cells[5].lower(),
            )
        )
    return tasks


def snapshot(board_path: Path) -> Snapshot:
    text = read_text(board_path)
    objective = strip_code_fence(section(text, "OBJETIVOS"))
    return Snapshot(
        digest=digest_text(text),
        objective="" if is_empty_marker(objective) else objective,
        in_progress=section(text, "EN PROGRESO"),
        completed=section(text, "COMPLETADO"),
        blocked=section(text, "BLOQUEADO"),
        tasks=parse_tasks(text),
    )


def task_key(task: Task) -> str:
    return task.task_id


def relevant_tasks(tasks: Iterable[Task], agent: str) -> list[Task]:
    if agent == "all":
        return list(tasks)
    return [task for task in tasks if task.agent in {agent, "ambos", "both", "all"}]


def diff_snapshots(previous: Snapshot | None, current: Snapshot, agent: str) -> list[dict[str, object]]:
    if previous is None:
        approved = [task for task in relevant_tasks(current.tasks, agent) if task.approved]
        return [
            {
                "type": "baseline",
                "objective_active": bool(current.objective),
                "approved_tasks": [asdict(task) for task in approved],
            }
        ]

    events: list[dict[str, object]] = []
    if previous.objective != current.objective:
        events.append(
            {
                "type": "objective_changed",
                "active": bool(current.objective),
                "objective": current.objective,
            }
        )

    previous_tasks = {task_key(task): task for task in relevant_tasks(previous.tasks, agent)}
    current_tasks = {task_key(task): task for task in relevant_tasks(current.tasks, agent)}
    for task_id, task in current_tasks.items():
        old = previous_tasks.get(task_id)
        if task.approved and (old is None or not old.approved):
            events.append({"type": "task_approved", "task": asdict(task)})
        elif old is not None and old.approved and not task.approved:
            events.append({"type": "task_unapproved", "task": asdict(task)})
        elif old is not None and asdict(old) != asdict(task):
            events.append({"type": "task_changed", "task": asdict(task)})

    if previous.in_progress != current.in_progress:
        events.append({"type": "in_progress_changed"})
    if previous.completed != current.completed:
        events.append({"type": "completed_changed"})
    if previous.blocked != current.blocked:
        events.append({"type": "blocked_changed"})
    return events


def load_state(path: Path) -> Snapshot | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return Snapshot(
            digest=raw["digest"],
            objective=raw.get("objective", ""),
            in_progress=raw.get("in_progress", ""),
            completed=raw.get("completed", ""),
            blocked=raw.get("blocked", ""),
            tasks=[Task(**item) for item in raw.get("tasks", [])],
        )
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return None


def save_state(path: Path, value: Snapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(value), ensure_ascii=False, indent=2), encoding="utf-8")


def emit(events: list[dict[str, object]], log_path: Path | None) -> None:
    if not events:
        return
    now = datetime.now().isoformat(timespec="seconds")
    lines = [json.dumps({"ts": now, **event}, ensure_ascii=False) for event in events]
    for line in lines:
        print(line, flush=True)
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            for line in lines:
                handle.write(line + "\n")


def resolve_default_board() -> Path:
    return Path(__file__).resolve().parents[1] / "TASKBOARD.md"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch TASKBOARD.md for CyberAgent coordination changes.")
    parser.add_argument("--board", type=Path, default=resolve_default_board(), help="Path to TASKBOARD.md.")
    parser.add_argument("--agent", choices=("codex", "claude", "all"), default="codex")
    parser.add_argument("--interval", type=float, default=2.0, help="Polling interval in seconds.")
    parser.add_argument("--once", action="store_true", help="Read once, emit current state, and exit.")
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("data/taskboard_listener_state.json"),
        help="Local state file used to compare changes between runs.",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=Path("logs/taskboard_listener.log"),
        help="JSONL event log path. Use --log none to disable.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    board_path = args.board.resolve()
    log_path = None if str(args.log).lower() == "none" else args.log
    previous = load_state(args.state)

    if not board_path.exists():
        print(f"TASKBOARD not found: {board_path}", file=sys.stderr)
        return 2

    while True:
        current = snapshot(board_path)
        events = diff_snapshots(previous, current, args.agent)
        emit(events, log_path)
        save_state(args.state, current)
        previous = current
        if args.once:
            return 0
        time.sleep(max(args.interval, 0.5))


if __name__ == "__main__":
    raise SystemExit(main())
