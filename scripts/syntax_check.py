#!/usr/bin/env python3
"""Check Python syntax for all .py files in the project. Exit 1 if any error."""
import ast, sys
from pathlib import Path

ROOT    = Path(__file__).parent.parent
EXCLUDE = {".venv", "__pycache__", ".git", "build", "dist", "node_modules"}

errors:  list[str] = []
checked: int       = 0

for py in ROOT.rglob("*.py"):
    if any(part in EXCLUDE for part in py.parts):
        continue
    try:
        ast.parse(py.read_text(encoding="utf-8", errors="replace"))
        checked += 1
    except SyntaxError as e:
        errors.append(f"  {py.relative_to(ROOT)}: line {e.lineno} — {e.msg}")

print(f"Checked {checked} Python files.")
if errors:
    print(f"\nSYNTAX ERRORS ({len(errors)}):")
    for err in errors:
        print(err)
    sys.exit(1)
else:
    print("All files OK.")
