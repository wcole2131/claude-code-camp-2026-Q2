---
name: mud-player
description: Play the tbaMUD (a CircleMUD/DikuMUD variant) running on localhost:4000, using the existing character dummy/helloworld, and pursue long-term goals (reaching a target level, hunting down a specific monster) across many separate play sessions using persistent memory files. Use this skill whenever the user asks to play, explore, log into, or interact with "the mud", "tbamud", "circlemud", or a telnet game on port 4000 -- including exploring rooms, fighting, chatting, checking inventory/stats, leveling up, or any other in-game action. Also use it for anything involving connecting to or scripting a telnet session against this specific MUD, even if the user doesn't say "play" explicitly (e.g. "check my mud character's inventory", "what room am I in", "kill the rat in the temple", "keep grinding toward level 7").
---

# Playing the tbaMUD

This MUD is a live, persistent, stateful telnet session -- unlike a normal
one-shot shell command, "logged in and standing in a room" is state that has
to survive between separate tool calls. These scripts solve that by holding
the actual `telnet` client open inside a detached `tmux` session in the
background; each script call attaches to that same session to send a command
or read output, then detaches again. The MUD connection itself is never
re-established per call -- only the very first `mud_start.sh` opens it.

All scripts live in `scripts/` next to this file and are self-contained bash
(they auto-locate their own directory, so call them by absolute or relative
path from anywhere). Credentials and connection settings default to this
project's dummy/helloworld character on localhost:4000, configurable via env
vars in `scripts/mud_env.sh` if that ever changes.

## Workflow

1. **Start the session once per play session:**
   `scripts/mud_start.sh`
   This opens telnet, logs in as `dummy`/`helloworld`, walks through the
   "press return" MOTD gate and the main menu, and lands you in the game
   world. It prints the initial room description. If a session is already
   running, it's a no-op that just tells you so -- safe to call defensively
   before sending commands if you're unsure of the current state.

2. **Load persistent memory, once per session, right after starting:**
   `scripts/mud_init_memory.sh`, then Read `data/player.md` and
   `data/world.md`.
   See "Long-term memory" below -- this is what lets goals like "reach level
   7" or "defeat a specific monster" survive across many separate
   conversations, since nothing else about this task persists in your
   context once a conversation ends.

3. **Issue any in-game command:**
   `scripts/mud_send.sh <command...>`
   e.g. `scripts/mud_send.sh look`, `scripts/mud_send.sh north`,
   `scripts/mud_send.sh kill rat`, `scripts/mud_send.sh say hello there`.
   All arguments are joined into one command line, so multi-word commands
   don't need quoting. It sends the line, waits briefly for the MUD to
   respond, and prints only the new output produced since the last read.

4. **Passively check for new output without acting:**
   `scripts/mud_read.sh`
   Useful when something might be happening on its own (combat rounds
   ticking, another player sending a tell, a room's periodic messages) and
   you want to see it without triggering a new action. Never sends
   anything to the MUD, so it's always safe to call speculatively.

5. **Check connection health:**
   `scripts/mud_status.sh`
   Shows whether the tmux session exists and the last few lines on screen,
   without consuming the read offset (so it won't cause `mud_read.sh` to
   report "no new output" afterward).

6. **Update memory as things happen, and again before stopping:**
   Edit `data/player.md` / `data/world.md` directly. See "Long-term memory"
   below for what's worth recording.

7. **End the session:**
   `scripts/mud_stop.sh`
   Sends `quit` and tears down the tmux session cleanly. Call this when
   done playing, or before `mud_start.sh` if you want to force a fresh
   reconnect (e.g. after the connection drops).

## Reading command output

Each in-game reply ends with a status-line prompt that looks like:
```
23H 100M 84V (news) (motd) >
```
(hitpoints/mana/movement). That prompt is your signal that a command's
output has fully arrived -- if a response looks cut off without one, the MUD
may still be producing output; call `mud_read.sh` again after a short pause.

## Long-term memory

A MUD character's actual progress (level, exp, location, inventory) is
tracked by the game server and survives on its own. What does *not* survive
is everything about the conversation: your stated goals, the reasoning
behind them, and the mental map you built up while exploring. If a session
starts, plays for a while, and ends, the next session has no memory of any
of that unless it's written down somewhere the next session will read --
that's what `data/player.md` and `data/world.md` are for.

- **`data/player.md`** -- the character's status snapshot, the long-term
  goals checklist (reach level 7; defeat a chosen monster), a short
  progress log, known skills, and strategy notes.
- **`data/world.md`** -- the map as discovered so far (rooms, exits, how
  they connect), points of interest (shops, guilds, trainers), and notes on
  monsters encountered (location, difficulty, whether they're worth
  fighting).

Templates for both live in `assets/` and `scripts/mud_init_memory.sh` seeds
`data/player.md` / `data/world.md` from them the first time (it never
overwrites a file that already has content, so it's safe to call every
session).

**Choosing the monster goal:** if `data/player.md` still shows the goal
monster as "not yet chosen", part of the session's job is to scout for a
reasonable candidate -- something that reads as a real challenge around
level 7 (check a mob's description, ask around, or just use judgment about
how tough something sounds) -- and record its name, location, and reasoning
in the goals section.

**What to actually write down:** don't try to log every command -- that
defeats the purpose and turns the file into noise nobody will re-read.
Update memory when something has actually changed that a future session
would want to know: a level-up, a death, a newly discovered room or shop, a
notable monster worth remembering, progress toward either long-term goal,
or a lesson learned the hard way. A good rule of thumb: if you asked
yourself "will I need to know this again later," and the answer is yes,
that's the moment to write it down -- not at the very end of the session
from memory, since details fade and get generalized away. Check off goals
in the checklist as they're achieved, and update `Last updated:` at the top
of whichever file changed.

## Playing well

Treat this like actually inhabiting the game: read room descriptions before
deciding where to go, check `look` after moving, and react to what other
output tells you (low HP, aggressive mobs, tells from other players) rather
than blindly executing a pre-planned sequence of commands. If the user gives
a high-level goal ("go explore", "level up a bit", "see who's online"),
translate it into a sensible sequence of individual MUD commands one at a
time, checking output between each rather than guessing several moves ahead.

If a command's output is confusing or a login gets stuck somewhere
unexpected, see `references/protocol.md` for the exact probed sequence of
prompts (name/password/MOTD/menu) this MUD uses, and troubleshooting notes
for reconnecting after a dropped connection.
