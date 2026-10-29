# baskingspot/skills: agent skills for Zig. README.md says what ships here,
# AGENTS.md holds the conventions, and docs/slop/ holds the design notes.

[private]
default:
    @just --list

[doc("Format the Markdown, the workflows, and the lint script")]
[group("lint")]
fmt:
    nix fmt
    oxfmt README.md AGENTS.md CHANGELOG.md skills eval .github
    ruff format scripts
    just --fmt

[doc("Check every skill against the specification and this repo's rules")]
[group("lint")]
check:
    #!/usr/bin/env bash
    set -euo pipefail
    vendored=eval/scaffold/.agents/skills

    for dir in skills/*/; do
        skills-ref validate "$dir"
    done
    ./scripts/check_skills.py skills

    # The scaffold is what an eval run starts from, so a copy that has drifted is
    # an eval that measures a skill nobody ships. The vendor recipe writes it.
    stale=0
    for dir in skills/*/; do
        name=$(basename "$dir")
        if [ ! -d "$vendored/$name" ]; then
            echo "$vendored/$name is missing. Run: just vendor" >&2
            stale=1
        elif ! diff -r "$dir" "$vendored/$name"; then
            echo "$vendored/$name is stale. Run: just vendor" >&2
            stale=1
        fi
    done
    for dir in "$vendored"/*/; do
        name=$(basename "$dir")
        if [ ! -d "skills/$name" ]; then
            echo "$vendored/$name is not a skill. Run: just vendor" >&2
            stale=1
        fi
    done
    if [ "$stale" -ne 0 ]; then
        exit 1
    fi
    echo "the eval scaffold matches skills/"

[doc("Check formatting, run the skill checks, and lint the workflows")]
[group("lint")]
lint: check
    nix fmt -- --ci
    oxfmt --check README.md AGENTS.md CHANGELOG.md skills eval .github
    ruff check scripts
    ruff format --check scripts
    ty check scripts
    actionlint
    zizmor .
    just --fmt --check

[doc("Copy the skills into the eval scaffold, where runs discover them")]
[group("eval")]
vendor:
    #!/usr/bin/env bash
    set -euo pipefail
    rm -rf eval/scaffold/.agents/skills
    mkdir -p eval/scaffold/.agents/skills
    cp -r skills/*/ eval/scaffold/.agents/skills/

    # A run can only cite what it saw, and it can only cite a commit.
    revision=$(git rev-parse --short HEAD)
    if [ -n "$(git status --porcelain -- skills)" ]; then
        echo "vendored from $revision with uncommitted skill changes"
        echo "commit them before a run, or the results cannot cite a revision"
    else
        echo "vendored from $revision"
    fi

[doc("Print each skill's size and the description an agent pays for every turn")]
[group("list")]
sizes:
    ./scripts/check_skills.py --sizes skills

[doc("Everything CI runs")]
[group("ci")]
ci: lint
