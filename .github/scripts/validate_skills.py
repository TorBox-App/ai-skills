#!/usr/bin/env python3
"""Check every skill in skills/ and the plugin manifests in .claude-plugin/.

Usage: python .github/scripts/validate_skills.py [repo_root]

Needs PyYAML. Exits 1 and prints one line per problem when anything is wrong.
The skill rules are the Agent Skills ones: https://agentskills.io/specification
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import yaml

NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024

# Each problem is (path relative to the repo root, 1-based line, message).
problems: list[tuple[str, int, str]] = []


def problem(path: Path, message: str, line: int = 1) -> None:
    problems.append((path.relative_to(ROOT).as_posix(), line, message))


def read_frontmatter(skill_file: Path) -> dict | None:
    """Return the parsed frontmatter, or None after recording why it is unusable."""
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].rstrip() != "---":
        problem(skill_file, "must start with a '---' line that opens the YAML frontmatter")
        return None
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.rstrip() == "---")
    except StopIteration:
        problem(skill_file, "frontmatter is never closed: add a '---' line after it")
        return None
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        line = mark.line + 2 if mark else 1  # +1 for the opening '---', +1 for 1-based
        problem(skill_file, "frontmatter is not valid YAML: " + " ".join(str(error).split()), line)
        return None
    if not isinstance(data, dict):
        problem(skill_file, "frontmatter must be a set of 'key: value' lines")
        return None
    if not "\n".join(lines[end + 1 :]).strip():
        problem(skill_file, "has no instructions after the frontmatter", end + 1)
    return data


def check_skill(skill_dir: Path) -> None:
    entries = {entry.name for entry in skill_dir.iterdir()}
    skill_file = skill_dir / "SKILL.md"
    if "SKILL.md" not in entries:
        wrong_case = sorted(name for name in entries if name.lower() == "skill.md")
        hint = f" (found '{wrong_case[0]}': the name is case-sensitive)" if wrong_case else ""
        problem(skill_dir, "has no SKILL.md" + hint)
        return

    frontmatter = read_frontmatter(skill_file)
    if frontmatter is None:
        return

    name = frontmatter.get("name")
    if not isinstance(name, str) or not name:
        problem(skill_file, "frontmatter needs a 'name' that is a non-empty string")
    else:
        if name != skill_dir.name:
            problem(
                skill_file,
                f"name '{name}' does not match its folder '{skill_dir.name}': "
                "rename one so they are identical",
            )
        if len(name) > MAX_NAME_LENGTH:
            problem(skill_file, f"name is {len(name)} characters; the limit is {MAX_NAME_LENGTH}")
        if not NAME_PATTERN.match(name):
            problem(
                skill_file,
                f"name '{name}' may use only lowercase letters, digits and single hyphens, "
                "and cannot start or end with a hyphen",
            )

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description.strip():
        problem(skill_file, "frontmatter needs a 'description' that is a non-empty string")
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        problem(
            skill_file,
            f"description is {len(description)} characters; the limit is {MAX_DESCRIPTION_LENGTH}",
        )


def check_skills() -> int:
    skills_root = ROOT / "skills"
    if not skills_root.is_dir():
        problem(ROOT, "has no skills/ directory")
        return 0
    skill_dirs = sorted(
        entry for entry in skills_root.iterdir() if entry.is_dir() and not entry.name.startswith(".")
    )
    if not skill_dirs:
        problem(skills_root, "contains no skill folders")
    for skill_dir in skill_dirs:
        check_skill(skill_dir)
    return len(skill_dirs)


def read_json(path: Path) -> dict | None:
    if not path.is_file():
        problem(path.parent, f"is missing {path.name}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        problem(path, f"is not valid JSON: {error.msg}", error.lineno)
        return None
    if not isinstance(data, dict):
        problem(path, "must contain a JSON object")
        return None
    return data


def check_manifests() -> None:
    marketplace_file = ROOT / ".claude-plugin" / "marketplace.json"
    marketplace = read_json(marketplace_file)
    if marketplace is None:
        return

    if not isinstance(marketplace.get("name"), str) or not marketplace["name"]:
        problem(marketplace_file, "needs a 'name'")
    owner = marketplace.get("owner")
    if not isinstance(owner, dict) or not owner.get("name"):
        problem(marketplace_file, "needs an 'owner' with a 'name'")
    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or not entries:
        problem(marketplace_file, "needs a non-empty 'plugins' list")
        return

    for index, entry in enumerate(entries):
        where = f"plugins[{index}]"
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("source"):
            problem(marketplace_file, f"{where} needs a 'name' and a 'source'")
            continue
        source = entry["source"]
        if not isinstance(source, str):
            continue  # Fetched from somewhere else, so there is nothing local to check.
        if source != "." and not source.startswith("./"):
            problem(marketplace_file, f"{where} source '{source}' must start with './'")
            continue
        plugin_root = (ROOT / source).resolve()
        if not plugin_root.is_dir():
            problem(marketplace_file, f"{where} source '{source}' is not a directory in this repo")
            continue
        manifest_file = plugin_root / ".claude-plugin" / "plugin.json"
        if not manifest_file.is_file():
            continue  # Allowed: the marketplace entry then acts as the manifest.
        manifest = read_json(manifest_file)
        if manifest is not None and manifest.get("name") != entry["name"]:
            problem(
                manifest_file,
                f"name '{manifest.get('name')}' does not match the marketplace entry "
                f"'{entry['name']}': people install by the entry name, so keep them identical",
            )


def main() -> int:
    skill_count = check_skills()
    check_manifests()

    if not problems:
        print(f"OK: {skill_count} skill(s) and the plugin manifests are valid.")
        return 0

    in_github_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for path, line, message in problems:
        print(f"{path}: {message}")
        if in_github_actions:
            escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
            print(f"::error file={path},line={line}::{escaped}")
    print(f"\n{len(problems)} problem(s) found.")
    return 1


ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    sys.exit(main())
