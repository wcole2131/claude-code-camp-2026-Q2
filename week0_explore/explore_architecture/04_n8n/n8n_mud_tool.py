# --- n8n setup -------------------------------------------------------------
# 1. On the machine with tmux + telnet installed, start the bridge and leave
#    it running:
#      python3 mud.py serve --port 8787
# 2. In n8n: AI Agent node -> Add Tool -> Code Tool.
#      - Name: mud_player  (or similar)
#      - Description (tells the LLM how to call it): "Play a MUD. Input is
#        either a raw in-game command to send (e.g. 'look', 'say hello',
#        'north'), or one of the control words: start, stop, status, read,
#        init-memory."
#      - Language: Python (Beta)
#      - Code: paste everything below this comment block into the code box.
# 3. If n8n and the bridge aren't on the same host, change MUD_BRIDGE_URL and
#    make sure the bridge's port is reachable from n8n (it binds to
#    127.0.0.1 by default -- edit cmd_serve's ThreadingHTTPServer host in
#    mud.py, e.g. to "0.0.0.0", if you need it reachable remotely).
# -----------------------------------------------------------------------

import json
import urllib.error
import urllib.request

MUD_BRIDGE_URL = "http://127.0.0.1:8787"
CONTROL_WORDS = {"start", "stop", "status", "read", "init-memory"}

raw = (query or "").strip()

if not raw:
    action, command = "status", []
else:
    first_word = raw.split(None, 1)[0].lower()
    if first_word in CONTROL_WORDS:
        action, command = first_word, []
    else:
        action, command = "send", raw.split()

request = urllib.request.Request(
    f"{MUD_BRIDGE_URL}/{action}",
    data=json.dumps({"command": command}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read())
except urllib.error.URLError as exc:
    result = {"ok": False, "output": f"Could not reach MUD bridge at {MUD_BRIDGE_URL}: {exc}"}

return result.get("output", "")
