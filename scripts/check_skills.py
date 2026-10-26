#!/usr/bin/env python3
"""Check every skill against the rules that skills-ref does not.

`skills-ref validate` covers the specification: the frontmatter fields, their
limits, and the name matching the directory. It says nothing about whether a
skill routes or whether it is small enough to load. Those are this repo's
three rules:

- The description states when the skill fires. An agent sees only the name and
  the description until it loads the body, so a description without a trigger
  is a skill that never fires.
- The body fits the budget. A skill over it holds attention nobody spends well;
  the cure is to move reference into `references/` behind a link.
- Every relative link resolves, in the body and in every file it ships. A skill
  that points at a file it does not have sends the agent to a dead end it cannot
  see.
- Every file under `references/` is reachable from `SKILL.md`. A reference
  nothing links to is a file an agent pays to clone and never reads.
- No two skills describe the same moment. Two descriptions that overlap make the
  model choose between them, which is a coin flip on every task.

Pass `--sizes` to print the budget as a table instead.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

# A description has to say when the skill applies, not only what it does. These
# are the phrasings the org's skills use. A description carrying none of them is
# either doing something else instead or leaving the trigger to the reader.
TRIGGERS = ("Use when", "Use before", "Use during", "Triggers on", "Use at")

# The Agent Skills guidance puts a body under about 500 lines or 5,000 tokens.
# Words are the honest proxy for tokens in prose; 4,000 words is roughly 5,200.
MAX_LINES = 500
MAX_WORDS = 4000

# Two descriptions sharing more than this much vocabulary are routing to the same
# moment. The number is a judgement call, and it is deliberately loose, because a
# false positive is cheap to argue with and a missed collision is not.
MAX_OVERLAP = 0.5
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "has",
        "have",
        "how",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "not",
        "of",
        "on",
        "or",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "use",
        "used",
        "when",
        "where",
        "which",
        "while",
        "with",
        "you",
        "your",
    }
)

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)")
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


def properties(directory: Path) -> dict[str, str]:
    """Name and description, parsed by skills-ref so every YAML form works."""
    result = subprocess.run(
        ["skills-ref", "read-properties", str(directory)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def body_of(text: str) -> str:
    """The Markdown after the frontmatter, which is what a skill loads."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "".join(lines[index + 1 :])
    return text


def check(directory: Path) -> list[str]:
    problems: list[str] = []
    text = (directory / "SKILL.md").read_text(encoding="utf-8")
    fields = properties(directory)
    body = body_of(text)

    description = fields.get("description", "")
    if not any(trigger in description for trigger in TRIGGERS):
        problems.append(
            f"{directory.name}: the description states no trigger. Add a "
            f"sentence starting with one of: {', '.join(TRIGGERS)}."
        )

    words = len(body.split())
    lines = len(body.splitlines())
    if words > MAX_WORDS:
        problems.append(
            f"{directory.name}: the body is {words} words, over the {MAX_WORDS} "
            f"budget. Move reference into references/ and link it."
        )
    if lines > MAX_LINES:
        problems.append(
            f"{directory.name}: the body is {lines} lines, over the {MAX_LINES} "
            f"budget. Move reference into references/ and link it."
        )

    linked: set[str] = set()
    for page in sorted(directory.rglob("*.md")):
        for target in LINK.findall(page.read_text(encoding="utf-8")):
            if SCHEME.match(target) or target.startswith("#"):
                continue
            path = target.split("#", 1)[0]
            if not path:
                continue
            resolved = (page.parent / path).resolve()
            linked.add(str(resolved))
            if not resolved.exists():
                where = page.relative_to(directory)
                problems.append(
                    f"{directory.name}: {target} does not exist, from {where}."
                )

    references = directory / "references"
    if references.is_dir():
        for reference in sorted(references.glob("**/*.md")):
            if str(reference.resolve()) not in linked:
                problems.append(
                    f"{directory.name}: {reference.relative_to(directory)} "
                    f"is linked from nothing, so nothing reads it."
                )

    return problems


def words(text: str) -> set[str]:
    """The significant vocabulary of a description, for comparing two of them."""
    cleaned = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return {word for word in cleaned.split() if len(word) > 3 and word not in STOPWORDS}


def collisions(directories: list[Path]) -> list[str]:
    """Two skills routed at the same moment make the model pick one at random."""
    problems: list[str] = []
    described = [
        (directory.name, words(properties(directory).get("description", "")))
        for directory in directories
    ]
    for index, (name, first) in enumerate(described):
        for other, second in described[index + 1 :]:
            if not first or not second:
                continue
            shared = len(first & second) / len(first | second)
            if shared > MAX_OVERLAP:
                problems.append(
                    f"{name} and {other}: descriptions overlap {shared:.0%}, which "
                    f"means both claim the same moment. Narrow one, or merge them."
                )
    return problems


def sizes(directory: Path) -> str:
    fields = properties(directory)
    text = (directory / "SKILL.md").read_text(encoding="utf-8")
    body = body_of(text)
    description = len(fields.get("description", ""))
    return (
        f"{fields.get('name', directory.name):28} "
        f"{description:5} desc chars  "
        f"{len(body.split()):5} body words  "
        f"{len(body.splitlines()):4} lines"
    )


def main(argv: list[str]) -> int:
    table = "--sizes" in argv
    roots = [Path(argument) for argument in argv if not argument.startswith("-")]
    if not roots:
        print("usage: check_skills.py [--sizes] DIR...", file=sys.stderr)
        return 2

    directories = sorted(
        path.parent for root in roots for path in root.glob("*/SKILL.md")
    )
    if not directories:
        print(
            f"no skills found under {', '.join(str(root) for root in roots)}",
            file=sys.stderr,
        )
        return 1

    if table:
        for directory in directories:
            print(sizes(directory))
        return 0

    problems = [problem for directory in directories for problem in check(directory)]
    problems += collisions(directories)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"{len(directories)} skills pass the repo rules")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
