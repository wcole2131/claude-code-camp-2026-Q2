# MudManager

The MudManager has the following responsibilities:

- manages long-lived telnet sessions
- manages the multi-step process of logging back in
- provides generic primitives for MUD commands

## Build the Gem

From this directory:

```sh
gem build mud_manager.gemspec
gem install ./mud_manager-0.1.0.gem
```

Expected output:

```text
MudManager
```

## Uninstall

```sh
gem uninstall mud_manager
```

## CLI

Installing the gem also installs a `mud-manager` executable: an interactive
raw-command prompt against a CircleMUD server. Whatever you type is sent to
the MUD as-is, and the response is printed back.

```sh
mud-manager --host localhost --port 4000
mud-manager --name YourCharacterName --password yourpassword
```

Options: `--host`, `--port`, `--timeout`, `--name` (or `$MUD_NAME`),
`--password` (or `$MUD_PASSWORD`), `--help`. Without `--name`/`--password` you
land at the login prompt and can type the name/password dance manually.
Ctrl-D disconnects the client.

## Examples

Test the live session:

```sh
MUD_NAME=YourCharacterName MUD_PASSWORD=yourpassword ruby mud_manager/examples/live_session_test.rb
```

If you are already inside the `mud_manager` directory, run:

```sh
MUD_NAME=YourCharacterName MUD_PASSWORD=yourpassword ruby examples/live_session_test.rb
```
