# Instructions for any coding agent working on this repo

This file is read by more than one agent — local Claude Code (as `CLAUDE.md`)
and Codex (as `AGENTS.md`, which is a symlink to this same file, not a copy).
Everything below applies to whichever agent is reading it. Where something
applies to only one agent, it says so by name.

You are executing `orin_bringup_plan.md` (in the LAKSA claude.ai project) for
an autonomous RC car. A cloud Claude session is tracking this work and will
review your results by reading this repo — **do not wait for it, and do not
expect a reply here.** Your job each run: do the task, write a structured
result file, commit, push. That's the entire sync mechanism, for every agent.

## Non-negotiable safety rules (do not route around these, ever)

1. **You never type the battery-unplugged confirmation phrase yourself.**
   `drive_command_loopback_test.py` requires a human to type
   `battery is unplugged` interactively (or pass `--yes-i-am-sure`, which you
   must NEVER pass — that flag exists for scripted CI, not for you skipping a
   physical safety check). Before running that script, stop and ask the
   person at the keyboard to confirm out loud that the main battery is
   physically disconnected, then let *them* type the confirmation, or hand
   them the exact command to run themselves.
2. **You are never the one who watches the car.** Any task that says
   "observe", "confirm centring", "watch the VESC LED", or similar (Phase B,
   Phase C) needs a human physically present and watching the hardware. You
   can prepare and run the software side and read back telemetry, but you do
   not mark those tasks done — the human does, in the result file, based on
   what they saw.
3. **No VESC configuration writes** (Phase D) without an explicit go-ahead
   from the person for that specific change. Read-only telemetry queries are
   fine any time.
4. **Only one DriveCommand publisher may run at a time.** Before starting
   `drive_command_loopback_test.py` or `laksa_teleop_supervisor`, confirm no
   other command publisher is already running (`ros2 topic info /laksa/command
   --verbose` should show at most the one publisher you're about to start).
5. If a step's "Done when" condition in `orin_bringup_plan.md` isn't met,
   say so plainly in the result file and stop — don't proceed to the next
   task on a guess, and don't loosen a check to make it pass.

## Reaching the Orin

SSH to the Orin over the network (no direct USB tether needed for anything
in Phase A/E below). The SSH config alias is **`dev-orin`** (set up in
`~/.ssh/config` on the WSL machine):

```
ssh dev-orin
```

Use `dev-orin` as the host in every rsync/ssh command below — not `orin`,
which was a placeholder in earlier drafts of this file.

## Per-task workflow

For each task (A1a, A1b, A3 install, etc.):

1. Read the task's row in `orin_bringup_plan.md` and the relevant section of
   `esp32_installed_firmware_findings.md` in the project docs (ask the human
   to paste these in if you can't reach the claude.ai project directly).
2. `rsync -av --exclude='.git' src/ dev-orin:~/laksa_ws/src/orin-bringup/src/`
   from wherever this repo is checked out (WSL, not the Orin) to push the
   current code over, then `ssh dev-orin` and `colcon build --symlink-install`
   there if not already built. **The Orin never runs git and never needs GitHub
   credentials of its own** — it's a plain SSH+rsync execution target, full
   stop. All git operations (commit, push, pull) happen on the machine that
   has this repo cloned with your GitHub auth (WSL).
3. Run the task over the same SSH connection. Capture full stdout/stderr.
4. Write `results/<task_id>_<UTC-timestamp>.md`:
   ```
   # A1a — laksa_readonly_check

   Run at: <UTC timestamp>
   Command: ros2 run laksa_bringup laksa_readonly_check
   Exit code: 0

   ## Output
   ```
   <full output>
   ```

   ## Verdict
   ALL MATCH (12/12 checks passed) — DriveCommand format not yet touched,
   proceeding to A1b is safe per this result alone.
   ```
   For anything requiring human observation (Phase B/C), leave a
   `## Human confirmation needed` section instead of a verdict, and stop.
5. Update `STATUS.md` (one line per task: task id, status, timestamp, link
   to its result file).
6. `git add results/ STATUS.md && git commit -m "results: <task id> <verdict>"
   && git push`.
7. Stop and wait to be told to continue to the next task — don't chain
   multiple hardware-touching tasks in one run without the human present for
   each one, even if the plan lists them consecutively.

## Multi-agent coordination (Claude Code + Codex, staggered pipeline)

The intended pattern: one agent executes the current gated step against the
Orin; the other reviews the most recent completed step and does groundwork
for the *next* one — drafting code, updating docs, researching, refining the
plan — while the first is still running. Coordination happens **only**
through this repo (commits, `STATUS.md`, `results/`) — neither agent messages
the other directly, and neither should assume the other's in-progress,
uncommitted work exists.

Hard rules for this to be safe rather than just fast:

1. **"Groundwork for the next step" never means running it early.** Drafting
   the script for A1b, writing its result-file template, or reviewing A1a's
   evidence is groundwork. Actually SSHing to the Orin and executing a step
   that hasn't been reached yet is not — that's the same violation as a
   single agent skipping ahead, just committed by the other one. A step is
   "reached" only when the previous row in `STATUS.md` shows a real result
   file with a passing verdict (or explicit human sign-off for an
   observation-only task), not when a plan or script for it exists.
2. **Only the agent that actually ran a hardware-touching task may mark it
   done in `STATUS.md`.** A review or groundwork pass on a task never flips
   its status — it can propose a verdict in its own commit message or a
   `notes/` file, but the authoritative status line is written by whichever
   agent (or human) produced the result file it points to.
3. **`git pull` before starting anything, every time.** Two agents committing
   to the same repo means your local view can be stale the moment you start.
   If `git pull` shows unexpected changes to a file you were about to write,
   stop and read them first rather than force-pushing over them.
4. **The one-command-publisher rule now covers both agents.** Before either
   agent starts `drive_command_loopback_test.py` or `laksa_teleop_supervisor`,
   check `STATUS.md` and `ros2 topic info /laksa/command --verbose` — not just
   your own memory of what you started — since the other agent may have a
   session open against the same Orin.
5. **Reviews are read-only by default.** "Codex reviews step N" means reading
   `results/`, the diff, and `orin_bringup_plan.md` — not editing what the
   executing agent already committed. Propose changes in a new commit or a
   note, don't rewrite someone else's result file.

## What NOT to do here

- Don't modify `laksa_interfaces` message definitions to make a check pass —
  if `laksa_readonly_check` disagrees with these definitions, that's a real
  finding (write it up, don't patch around it) until it's resolved against
  `esp32_installed_firmware_findings.md`.
- Don't enable `laksa_teleop_supervisor` (`enabled:=true`) or raise
  `max_abs_speed_mps` unless the person explicitly asks for that, and never
  before Phase C's stop-method gate is passed.
- Don't commit flash dumps, credentials, or Wi-Fi passwords to this repo
  (see `.gitignore`).
