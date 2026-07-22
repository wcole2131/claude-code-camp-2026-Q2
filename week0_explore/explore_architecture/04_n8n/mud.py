#!/usr/bin/env python3
"""MUD player CLI: connect to and play a MUD via a detached tmux session.

Consolidates the former mud_env.sh/mud_start.sh/mud_stop.sh/mud_status.sh/
mud_read.sh/mud_send.sh/mud_init_memory.sh scripts into one file. Each
subcommand is meant to be invoked as a separate, stateless process (e.g. by
an agent), with the tmux session and an on-disk offset file carrying state
between invocations.

Usage:
  mud.py start
  mud.py stop
  mud.py status
  mud.py read
  mud.py send <command text...>
  mud.py init-memory
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent

MUD_HOST = os.environ.get("MUD_HOST", "localhost")
MUD_PORT = os.environ.get("MUD_PORT", "4000")
MUD_USER = os.environ.get("MUD_USER", "dummy")
MUD_PASS = os.environ.get("MUD_PASS", "helloworld")
MUD_WAIT = float(os.environ.get("MUD_WAIT", "0.8"))

# Namespaced by MUD_USER so two different characters (e.g. two subagents each
# exporting a different MUD_USER) get an independent tmux session, read-offset
# state, and memory directory automatically, and don't collide or overwrite
# each other's data. Each can still be overridden individually if a caller
# needs a different layout.
MUD_SESSION = os.environ.get("MUD_SESSION", f"tbamud-{MUD_USER}")
MUD_STATE_DIR = Path(os.environ.get("MUD_STATE_DIR", str(DIR / ".state" / MUD_USER)))

# Project root is always 1 level above this script for this subagent layout.
MUD_PROJECT_ROOT = Path(os.environ.get("MUD_PROJECT_ROOT", str(DIR.parent)))
MUD_DATA_DIR = Path(os.environ.get("MUD_DATA_DIR", str(MUD_PROJECT_ROOT / "data" / MUD_USER)))

OFFSET_FILE = MUD_STATE_DIR / "offset"


# --- tmux helpers -----------------------------------------------------------

def has_session() -> bool:
    result = subprocess.run(
        ["tmux", "has-session", "-t", MUD_SESSION],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def capture_pane(scrollback: int = 5000) -> str:
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", MUD_SESSION, "-p", "-S", f"-{scrollback}"],
        capture_output=True, text=True,
    )
    return result.stdout


def pane_lines(scrollback: int = 5000) -> list[str]:
    return capture_pane(scrollback).splitlines()


def total_lines() -> int:
    return len(pane_lines())


def send_literal(text: str) -> None:
    subprocess.run(["tmux", "send-keys", "-t", MUD_SESSION, "-l", "--", text], check=True)


def send_enter() -> None:
    subprocess.run(["tmux", "send-keys", "-t", MUD_SESSION, "Enter"], check=True)


# Polls until $pattern (a regex) appears anywhere in the last ~300 lines of
# the pane, or $timeout seconds pass. The server's client-detection
# negotiation has variable timing, so login steps must wait for the actual
# prompt text rather than a fixed sleep -- a fixed sleep that's too short
# sends input before the prompt exists and desyncs the rest of the login
# sequence.
def wait_for_text(pattern: str, timeout: float = 10) -> bool:
    elapsed = 0.0
    while elapsed < timeout:
        if re.search(pattern, capture_pane(300)):
            return True
        time.sleep(0.2)
        elapsed += 0.2
    return False


# Polls until new output beyond $pre_total (a previously captured total line
# count) contains the in-game status prompt (e.g. "23H 100M 84V (news)
# (motd) >"), or $timeout seconds pass. Used after sending an in-game command
# to know the MUD has finished responding instead of guessing a fixed delay.
def wait_for_new_prompt(pre_total: int, timeout: float = 10) -> bool:
    elapsed = 0.0
    while elapsed < timeout:
        lines = pane_lines()
        if len(lines) > pre_total:
            new_part = "\n".join(lines[pre_total:])
            if re.search(r"[0-9]+H [0-9]+M [0-9]+V", new_part):
                time.sleep(0.3)  # grace period to catch trailing lines from the same batch
                return True
        time.sleep(0.2)
        elapsed += 0.2
    return False


# --- subcommands -------------------------------------------------------------

def cmd_start(_args) -> int:
    if has_session():
        print(
            f"Session '{MUD_SESSION}' is already running. "
            "Use 'mud.py read' to see recent output, or 'mud.py stop' to disconnect first."
        )
        return 0

    MUD_STATE_DIR.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.unlink(missing_ok=True)

    subprocess.run(["tmux", "new-session", "-d", "-s", MUD_SESSION, "-x", "200", "-y", "50"], check=True)
    subprocess.run(["tmux", "set-option", "-t", MUD_SESSION, "history-limit", "5000"], check=True)

    send_literal(f"telnet {MUD_HOST} {MUD_PORT}")
    send_enter()

    # The client-detection negotiation before the name prompt has variable
    # timing, so wait for the actual prompt text at each step rather than
    # guessing a fixed delay.
    def fail(msg: str) -> int:
        print(f"{msg} Current screen:", file=sys.stderr)
        print(capture_pane(), file=sys.stderr)
        return 1

    if not wait_for_text("By what name", 20):
        return fail("Timed out waiting for the name prompt.")
    send_literal(MUD_USER)
    send_enter()

    if not wait_for_text("Password:", 10):
        return fail("Timed out waiting for the password prompt.")
    send_literal(MUD_PASS)
    send_enter()

    if not wait_for_text("PRESS RETURN", 10):
        return fail("Timed out waiting for the MOTD screen.")
    send_enter()

    if not wait_for_text("Make your choice", 10):
        return fail("Timed out waiting for the main menu.")
    pre_total = total_lines()
    send_literal("1")
    send_enter()

    wait_for_new_prompt(pre_total, 10)  # best-effort; fall through either way

    print(f"Connected to {MUD_HOST}:{MUD_PORT} and logged in as {MUD_USER}.")
    print("----")
    return cmd_read(_args)


def cmd_stop(_args) -> int:
    if has_session():
        send_literal("quit")
        send_enter()
        time.sleep(1)
        subprocess.run(
            ["tmux", "kill-session", "-t", MUD_SESSION],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        print(f"Sent quit and closed session '{MUD_SESSION}'.")
    else:
        print("No active session to stop.")
    OFFSET_FILE.unlink(missing_ok=True)
    return 0


def cmd_status(_args) -> int:
    if has_session():
        print(f"Session '{MUD_SESSION}' is running ({MUD_HOST}:{MUD_PORT}, user {MUD_USER}).")
        print("----")
        print("\n".join(pane_lines()[-8:]))
    else:
        print(f"No active session named '{MUD_SESSION}'.")
    return 0


def cmd_read(_args) -> int:
    if not has_session():
        print("No active MUD session. Run 'mud.py start' first.", file=sys.stderr)
        return 1

    MUD_STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        last = int(OFFSET_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        last = 0

    lines = pane_lines()
    total = len(lines)

    if total > last:
        print("\n".join(lines[last:]))
    else:
        print("(no new output)")

    OFFSET_FILE.write_text(f"{total}\n")
    return 0


def cmd_send(args) -> int:
    if not args.command:
        print("Usage: mud.py send <command text...>", file=sys.stderr)
        return 1
    if not has_session():
        print("No active MUD session. Run 'mud.py start' first.", file=sys.stderr)
        return 1

    text = " ".join(args.command)
    pre_total = total_lines()
    send_literal(text)
    send_enter()

    # Wait for the next status prompt to know the MUD finished responding.
    # Commands that don't produce one (e.g. "quit") just fall through to the
    # plain wait below instead.
    if not wait_for_new_prompt(pre_total, 5):
        time.sleep(MUD_WAIT)

    return cmd_read(args)


def cmd_init_memory(_args) -> int:
    MUD_DATA_DIR.mkdir(parents=True, exist_ok=True)
    template_dir = DIR.parent / "assets"

    for name, template in (("player.md", "player_template.md"), ("world.md", "world_template.md")):
        target = MUD_DATA_DIR / name
        if not (target.exists() and target.stat().st_size > 0):
            shutil.copyfile(template_dir / template, target)
            print(f"Initialized {target} from template.")
        else:
            print(f"{target} already has content -- left untouched.")
    return 0


ACTIONS = {
    "start": cmd_start,
    "stop": cmd_stop,
    "status": cmd_status,
    "read": cmd_read,
    "send": cmd_send,
    "init-memory": cmd_init_memory,
}


# Runs an action the same way the CLI would, but captures whatever it prints
# instead of writing to the real stdout/stderr. Used by the HTTP bridge (see
# cmd_serve) so a caller like n8n's Python (Beta) Code Tool -- which cannot
# spawn tmux/telnet itself -- gets the same text a terminal user would see.
def run_action(action: str, command_words: list[str] | None = None) -> tuple[int, str]:
    func = ACTIONS.get(action)
    if func is None:
        return 1, f"Unknown action '{action}'. Valid actions: {', '.join(ACTIONS)}"

    args = argparse.Namespace(command=command_words or [])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            code = func(args)
        except Exception as exc:  # keep the bridge alive even if a command misbehaves
            print(f"Error: {exc}")
            code = 1
    return code, buf.getvalue()


# Minimal HTTP bridge (stdlib only) so a sandboxed caller with no subprocess
# access -- e.g. n8n's Python (Beta) Code Tool, which runs on Pyodide -- can
# drive the real tmux/telnet session over plain HTTP instead. Run this on the
# same host that has tmux/telnet installed:
#   python3 mud.py serve --port 8787
# Endpoints: POST /start /stop /status /read /init-memory, POST /send with a
# JSON body {"command": "look"} or {"command": ["say", "hello"]}.
def cmd_serve(args) -> int:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def _reply(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _dispatch(self, action: str, command: list[str]) -> None:
            code, output = run_action(action, command)
            self._reply(200 if code == 0 else 500, {"ok": code == 0, "output": output})

        def do_GET(self) -> None:  # e.g. GET /status, GET /read
            self._dispatch(self.path.strip("/") or "status", [])

        def do_POST(self) -> None:  # e.g. POST /send {"command": "look"}
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            command: list[str] = []
            if raw:
                try:
                    data = json.loads(raw)
                    command = data.get("command", [])
                    if isinstance(command, str):
                        command = command.split()
                except json.JSONDecodeError:
                    command = raw.decode().split()
            self._dispatch(self.path.strip("/") or "send", command)

        def log_message(self, fmt: str, *a) -> None:  # keep terminal quiet
            pass

    print(f"MUD bridge listening on http://127.0.0.1:{args.port} (actions: {', '.join(ACTIONS)})")
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
    return 0


# --- CLI ----------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="mud.py", description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser("start", help="Connect and log in (idempotent).").set_defaults(func=cmd_start)
    subparsers.add_parser("stop", help="Quit and tear down the session.").set_defaults(func=cmd_stop)
    subparsers.add_parser("status", help="Report session status without consuming the read offset.").set_defaults(func=cmd_status)
    subparsers.add_parser("read", help="Print new output since the last read/send.").set_defaults(func=cmd_read)

    send_parser = subparsers.add_parser("send", help="Send a command line and print the response.")
    send_parser.add_argument("command", nargs=argparse.REMAINDER, help="Command text to send.")
    send_parser.set_defaults(func=cmd_send)

    subparsers.add_parser(
        "init-memory", help="Seed data/player.md and data/world.md from templates."
    ).set_defaults(func=cmd_init_memory)

    serve_parser = subparsers.add_parser(
        "serve", help="Run an HTTP bridge so sandboxed callers (e.g. n8n) can drive the MUD."
    )
    serve_parser.add_argument("--port", type=int, default=8787)
    serve_parser.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
