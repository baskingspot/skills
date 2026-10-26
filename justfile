# baskingspot/skills: agent skills for Zig. README.md says what ships here,
# AGENTS.md holds the conventions, and docs/slop/ holds the design notes.

[private]
default:
    @just --list

[doc("Format the Markdown, the workflows, and the lint script")]
[group("lint")]
fmt:
    nix fmt
    oxfmt README.md AGENTS.md CHANGELOG.md skills .github
    ruff format scripts
    just --fmt

[doc("Check every skill against the specification and this repo's rules")]
[group("lint")]
check:
    for dir in skills/*/; do skills-ref validate "$dir"; done
    ./scripts/check_skills.py skills
    diff -r skills/zig-016 eval/scaffold/.agents/skills/zig-016
    diff -r skills/tiger-style eval/scaffold/.agents/skills/tiger-style

[doc("Check formatting, run the skill checks, and lint the workflows")]
[group("lint")]
lint: check
    nix fmt -- --ci
    oxfmt --check README.md AGENTS.md CHANGELOG.md skills .github
    ruff check scripts
    ruff format --check scripts
    ty check scripts
    actionlint
    zizmor .
    just --fmt --check

[doc("Copy the skills into the eval scaffold, where runs discover them")]
[group("eval")]
vendor:
    rm -rf eval/scaffold/.agents/skills
    mkdir -p eval/scaffold/.agents/skills
    cp -r skills/zig-016 skills/tiger-style eval/scaffold/.agents/skills/

[doc("Print each skill's size and the description an agent pays for every turn")]
[group("list")]
sizes:
    ./scripts/check_skills.py --sizes skills

[doc("Everything CI runs")]
[group("ci")]
ci: lint
