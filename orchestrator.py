# Scaffold only — review prompts and test manually before running autonomously
"""
PcCoach Level 1 Autonomous Orchestrator.

Accepts a task description, launches Claude Code sessions in a loop,
and checks feature completion after each session.

Usage:
    python orchestrator.py "Implement all failing compliance features"
    python orchestrator.py --max-sessions 5 "Fix affiliate disclosures"
"""

import json
import subprocess
import sys
import time
from pathlib import Path

FEATURES_PATH = Path("docs/features.json")
PROGRESS_PATH = Path("docs/progress.md")

INIT_PROMPT = """\
You are setting up the PcCoach harness for the first time.

1. Read the codebase thoroughly — backend/, frontend/, shared/, Makefile, \
   docker-compose files, and all .md files.
2. Create docs/features.json with all implemented and unimplemented features \
   (20-40 features, mark passes: true/false honestly).
3. Create docs/progress.md with current state, last session info, next \
   priority, and known issues.
4. Add session rules to CLAUDE.md (init.sh, progress.md, features.json).
5. Create init.sh (start services, health check, smoke test, run tests).
6. Commit everything with message: \
   "harness: add CLAUDE.md, features.json, progress.md, init.sh, orchestrator.py"
"""

CODING_PROMPT = """\
You are an autonomous coding agent working on PcCoach.

Task from orchestrator: {task}

Follow these steps exactly:

1. Run `bash init.sh` and abort if it fails. Do not proceed with a broken \
   environment.
2. Read docs/progress.md and docs/features.json.
3. Pick the highest-priority failing feature (lowest ID with passes: false). \
   If the orchestrator provided a specific task, prioritize features related \
   to that task.
4. Implement the feature. Test it end-to-end — run the relevant tests, \
   verify the endpoint or page works.
5. Update docs/features.json — set passes: true for the feature you completed. \
   Update notes if relevant.
6. Update docs/progress.md:
   - Set "Last Session" date, work done, branch, and commit hash.
   - Set "Next Priority" to the next failing feature.
   - Update "Known Issues" if you discovered or resolved any.
7. Commit with a descriptive message (e.g., "feat: add per-page affiliate \
   disclosure on build result page").
8. Exit cleanly. Do not start another feature in the same session.
"""


def load_features() -> dict:
    """Load and return the features.json file."""
    if not FEATURES_PATH.exists():
        return {}
    with open(FEATURES_PATH) as f:
        return json.load(f)


def count_features(data: dict) -> tuple[int, int]:
    """Return (passing, failing) feature counts."""
    features = data.get("features", [])
    passing = sum(1 for f in features if f.get("passes"))
    failing = sum(1 for f in features if not f.get("passes"))
    return passing, failing


def get_next_failing(data: dict) -> dict | None:
    """Return the first failing feature, or None if all pass."""
    for f in data.get("features", []):
        if not f.get("passes"):
            return f
    return None


def run_claude_session(prompt: str) -> int:
    """
    Launch a Claude Code CLI session with the given prompt.
    Returns the exit code.
    """
    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",
        "-p", prompt,
    ]
    print(f"\n{'='*60}")
    print("Launching Claude Code session...")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=str(Path.cwd()))
    return result.returncode


def main():
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py <task-description>")
        print('       python orchestrator.py --max-sessions N "<task>"')
        sys.exit(1)

    # Parse args
    max_sessions = 10
    args = sys.argv[1:]
    if args[0] == "--max-sessions":
        max_sessions = int(args[1])
        args = args[2:]

    task = " ".join(args)

    # Check if features.json exists; if not, run init
    if not FEATURES_PATH.exists():
        print("features.json not found — running initialization prompt...")
        exit_code = run_claude_session(INIT_PROMPT)
        if exit_code != 0:
            print(f"Init session failed with exit code {exit_code}")
            sys.exit(1)

    # Main loop
    for session_num in range(1, max_sessions + 1):
        data = load_features()
        passing, failing = count_features(data)
        print(f"\n--- Session {session_num}/{max_sessions} ---")
        print(f"Features: {passing} passing, {failing} failing")

        if failing == 0:
            print("\nAll features pass! Orchestrator complete.")
            sys.exit(0)

        next_feature = get_next_failing(data)
        if next_feature:
            print(f"Next target: {next_feature['id']} — {next_feature['description']}")

        prompt = CODING_PROMPT.format(task=task)
        exit_code = run_claude_session(prompt)

        if exit_code != 0:
            print(f"Session {session_num} exited with code {exit_code}")
            print("Waiting 10s before retrying...")
            time.sleep(10)

    # Exhausted sessions
    data = load_features()
    passing, failing = count_features(data)
    print(f"\nMax sessions reached. Features: {passing} passing, {failing} failing.")
    sys.exit(1 if failing > 0 else 0)


if __name__ == "__main__":
    main()
