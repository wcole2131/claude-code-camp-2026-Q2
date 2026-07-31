from __future__ import annotations

import queue
import threading
import time
from datetime import datetime
from typing import Any, ClassVar

from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, RichLog, Static

from .agent import Agent
from .repl import Repl
from .version import VERSION

# Ruby's exact ANSI hex palette (lib/boukensha/tui.rb's ANSI_COLORS), ported as-is
# rather than mapped onto Textual's named theme colors so both TUIs are visually
# equivalent, not just functionally equivalent.
ANSI_COLORS = {
    "cyan": "#00ffff",
    "bright_black": "#808080",
    "green": "#00ff00",
    "white": "#ffffff",
}


def _idle_live() -> dict[str, Any]:
    return {
        "active": False,
        "spinner_idx": 0,
        "start_time": None,
        "elapsed": 0.0,
        "current_action": "idle",
        "iteration": 0,
        "tool_call_count": 0,
        "turn_input_tokens": 0,
        "turn_output_tokens": 0,
    }


class Tui(App[None]):
    """Wraps a Repl instance and replaces its raw print/input I/O with a
    structured four-zone display, using textual in place of Ruby's charm
    (bubbletea + lipgloss + bubbles).

    The Repl continues to own session logic (turn counting, /commands, Agent
    dispatch). Tui registers an output callback and a logger subscriber on
    the Repl and drives a textual event loop on top of it.

    Layout (top -> bottom):
      +------------------------------------------------+
      |  conversation viewport (scrollable)             |
      +------------------------------------------------+
      |  <spinner> live progress line (hidden when idle)|
      +------------------------------------------------+
      |  boukensha> input box                           |
      +------------------------------------------------+
      |  status line (always-on)                        |
      +------------------------------------------------+
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #viewport {
        height: 1fr;
        border: none;
        scrollbar-size: 0 0;
    }

    #progress {
        height: 1;
    }

    #input-row {
        height: 1;
        layout: horizontal;
    }

    #prompt-label {
        width: auto;
    }

    #input-box {
        width: 1fr;
        border: none;
        background: transparent;
    }

    #status {
        height: 1;
    }
    """

    SPINNER_FRAMES: ClassVar[list[str]] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    TICK_SECONDS = 0.06

    def __init__(self, repl: Repl) -> None:
        super().__init__()
        self._repl = repl
        self._output_queue: queue.Queue[str] = queue.Queue()
        self._events: queue.Queue[dict[str, Any]] = queue.Queue()
        self._turn_count = 0
        self._session_input_tokens = 0
        self._session_output_tokens = 0
        self._interrupt: threading.Event | None = None
        self._live: dict[str, Any] = _idle_live()

    def start(self) -> None:
        self.run()

    # -- textual lifecycle -------------------------------------------------

    def compose(self) -> ComposeResult:
        yield RichLog(id="viewport", auto_scroll=True, wrap=True, highlight=False, markup=False)
        yield Static(id="progress")
        with Horizontal(id="input-row"):
            yield Static(id="prompt-label")
            yield Input(placeholder="Type a message…", id="input-box")
        yield Static(id="status")

    def on_mount(self) -> None:
        self._repl.on_output(self._output_queue.put)
        self._repl.logger.subscribe(self._events.put)
        self._output_queue.put(self._repl.banner())

        self.query_one("#prompt-label", Static).update(
            Text(Repl.PROMPT, style=Style(color=ANSI_COLORS["green"], bold=True))
        )
        self.query_one("#input-box", Input).focus()

        self.set_interval(self.TICK_SECONDS, self._on_tick)
        self._on_tick()

    # -- keyboard ------------------------------------------------------------

    def on_key(self, event: events.Key) -> None:
        if event.key in ("ctrl+c", "ctrl+d"):
            event.stop()
            event.prevent_default()
            self.exit()
        elif event.key == "escape":
            if self._interrupt is not None:
                self._interrupt.set()
            event.stop()
        elif event.key == "ctrl+l":
            self._repl.handle_command("/clear")
            self._turn_count = 0
            event.stop()
        elif event.key == "pageup":
            self.query_one("#viewport", RichLog).scroll_page_up()
            event.stop()
        elif event.key == "pagedown":
            self.query_one("#viewport", RichLog).scroll_page_down()
            event.stop()

    def on_input_submitted(self, message: Input.Submitted) -> None:
        text = message.value.strip()
        message.input.value = ""
        if not text:
            return

        if text.startswith("/"):
            result = self._repl.handle_command(text)
            if result == "quit":
                self.exit()
                return
            if text == "/clear":
                self._turn_count = 0
            return

        self._output_queue.put(f"> {text}")
        self._launch_turn(text)

    # -- agent turn (background thread) --------------------------------------

    def _launch_turn(self, text: str) -> None:
        self._interrupt = threading.Event()
        self._live = _idle_live()
        self._live["active"] = True
        self._live["start_time"] = time.monotonic()
        self._live["current_action"] = "Thinking…"
        self.run_worker(lambda: self._run_turn_worker(text), thread=True, exclusive=True)

    def _run_turn_worker(self, text: str) -> None:
        try:
            self._repl.run_turn(text, interrupt=self._interrupt)
        except KeyboardInterrupt:
            self._events.put({"phase": "turn_interrupted"})
        except Exception as e:  # noqa: BLE001
            self._events.put({"phase": "turn_error", "error": str(e)})
        finally:
            self._events.put({"phase": "turn_complete"})

    # -- tick / event draining -----------------------------------------------

    def _on_tick(self) -> None:
        self._drain_output()
        self._drain_events()
        if self._live["active"]:
            self._live["spinner_idx"] = (self._live["spinner_idx"] + 1) % len(self.SPINNER_FRAMES)
            if self._live["start_time"] is not None:
                self._live["elapsed"] = time.monotonic() - self._live["start_time"]
        self._render_progress()
        self._render_status()

    def _write_line(self, text: str) -> None:
        self.query_one("#viewport", RichLog).write(text)

    def _drain_output(self) -> None:
        while True:
            try:
                line = self._output_queue.get_nowait()
            except queue.Empty:
                break
            self._write_line(line)

    def _drain_events(self) -> None:
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)

    def _handle_event(self, event: dict[str, Any]) -> None:
        phase = str(event.get("phase", ""))

        if phase == "iteration":
            self._live["iteration"] = int(event.get("n") or 0)
            self._live["current_action"] = "Thinking…"

        elif phase == "tool_call":
            name = event.get("name")
            self._live["current_action"] = f"Calling tool: {name}"
            self._live["tool_call_count"] += 1

        elif phase == "tool_result":
            self._live["current_action"] = "Awaiting result…"

        elif phase == "response":
            usage = event.get("usage")
            if usage:
                itu = int(usage.get("input_tokens") or 0)
                otu = int(usage.get("output_tokens") or 0)
                self._live["turn_input_tokens"] += itu
                self._live["turn_output_tokens"] += otu
                self._session_input_tokens += itu
                self._session_output_tokens += otu

        elif phase == "turn_complete":
            self._live["active"] = False
            self._turn_count += 1

        elif phase == "turn_interrupted":
            self._write_line("[interrupted]")

        elif phase == "turn_error":
            self._live["active"] = False
            self._write_line(f"[error] {event.get('error')}")

    # -- rendering ------------------------------------------------------------

    def _render_progress(self) -> None:
        progress = self.query_one("#progress", Static)

        if self._live["active"]:
            frame = self.SPINNER_FRAMES[self._live["spinner_idx"]]
            action = self._live["current_action"]
            iteration = self._live["iteration"]
            max_iterations = Agent.MAX_ITERATIONS
            secs = int(self._live["elapsed"])
            itok = self._fmt_tokens(self._live["turn_input_tokens"])
            otok = self._fmt_tokens(self._live["turn_output_tokens"])
            calls = self._live["tool_call_count"]

            text = Text(
                f"{frame} {action}  (iter {iteration}/{max_iterations} · {secs}s · "
                f"↑ {itok} · ↓ {otok} · {calls} calls)",
                style=Style(color=ANSI_COLORS["cyan"]),
            )
        else:
            used = self._fmt_tokens(self._session_input_tokens)
            text = Text(
                f"  [ready]   ctx {used}   {self._turn_count} turns",
                style=Style(color=ANSI_COLORS["bright_black"]),
            )

        progress.update(text)

    def _render_status(self) -> None:
        status = self.query_one("#status", Static)

        ver = self._repl.version or VERSION
        model = self._repl.model or "(model)"
        used = self._fmt_tokens(self._session_input_tokens)
        tools = self._repl.context.tool_count
        clock = datetime.now().astimezone().strftime("%H:%M:%S")
        width = self.size.width or 80

        bar = f" boukensha v{ver} · {model}  ·  ctx {used}  ·  {tools} tools  ·  {clock} "
        status.update(Text(bar.ljust(width), style=Style(color=ANSI_COLORS["white"], bgcolor=ANSI_COLORS["bright_black"])))

    @staticmethod
    def _fmt_tokens(n: Any) -> str:
        n = int(n or 0)
        return f"{n / 1000.0:.1f}k" if n >= 1000 else str(n)
