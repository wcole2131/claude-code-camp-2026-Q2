# tbaMUD login/menu protocol (probed against localhost:4000)

This documents the raw exchange that `mud_start.sh` automates, in case a
session gets stuck somewhere unexpected and you need to debug it by hand
(e.g. via `tmux attach -t tbamud` or `mud_status.sh`).

## 1. Connection banner
Server sends a client-detection banner (telnet IAC negotiation + a TBAMUD
ASCII splash), then prompts:

```
By what name do you wish to be known?
```

Send the character name (`dummy`).

## 2. Password
```
Password:
```
Send the password (`helloworld`). The server negotiates telnet ECHO
suppression here, so the password may not be visible on screen -- that's
expected and doesn't affect the scripted login.

## 3. MOTD / press-return gate
```
*** PRESS RETURN:
```
Send a blank line (just Enter).

## 4. Main menu
```
Welcome to tbaMUD!
0) Exit from tbaMUD.
1) Enter the game.
2) Enter description.
3) Read the background story.
4) Change password.
5) Delete this character.

   Make your choice:
```
Send `1` to enter the game. (Options 2-5 are not automated by these scripts;
if you need them, use `mud_send.sh` manually after `mud_start.sh` reaches
this menu, or attach to the tmux session directly.)

## 5. In-game prompt
Once in the game, every command's output ends in a status-line prompt like:

```
23H 100M 84V (news) (motd) >
```

`H`/`M`/`V` are hitpoints/mana/movement. This prompt is how you can tell a
command has finished producing output.

## Notes
- `quit` from the in-game prompt logs the character out back to the main
  menu (step 4), it does not close the TCP connection by itself --
  `mud_stop.sh` also kills the tmux session afterward to fully disconnect.
- If the server disconnects the socket for any reason (idle timeout, reboot),
  the tmux pane will just show `Connection closed by foreign host.` and
  `mud_send.sh` will start silently failing to elicit new output. Run
  `mud_status.sh` to check, and `mud_stop.sh` + `mud_start.sh` to reconnect.
