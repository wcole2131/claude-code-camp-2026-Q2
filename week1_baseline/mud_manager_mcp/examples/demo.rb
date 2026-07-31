#!/usr/bin/env ruby
# frozen_string_literal: true

# Manual smoke test for ../bin/mud_manager_server, using the generic
# Boukensha::MCP client (lib/boukensha/mcp.rb in the ruby step, pulled in
# here via this directory's own Gemfile path dependency on it) -- the same
# client any language's Boukensha port would use, proving the MUD sidecar
# is reachable as a real MCP server, not through a MUD-specific hand-rolled
# protocol.
#
# Usage:
#   MUD_HOST=your.mud.host MUD_PORT=4000 MUD_NAME=YourChar MUD_PASSWORD=yourpass \
#     bundle exec ruby examples/demo.rb
#
# MUD_HOST defaults to "localhost", MUD_PORT defaults to "4000".
# Only read-only commands are sent (mud_status, look, check) plus a final
# mud_disconnect -- nothing that moves, fights, or otherwise mutates the
# character, so it's safe to run against a live server.

require "boukensha"

mcp_dir       = File.expand_path("..", __dir__)
server_script = File.join(mcp_dir, "bin", "mud_manager_server")

env = {
  "MUD_HOST"     => ENV.fetch("MUD_HOST", "localhost"),
  "MUD_PORT"     => ENV.fetch("MUD_PORT", "4000"),
  "MUD_NAME"     => ENV.fetch("MUD_NAME") { abort "demo: set MUD_NAME to your character's name" },
  "MUD_PASSWORD" => ENV.fetch("MUD_PASSWORD") { abort "demo: set MUD_PASSWORD to your character's password" }
}

puts "Connecting to #{env['MUD_HOST']}:#{env['MUD_PORT']} as #{env['MUD_NAME']}..."
puts "(spawning: bundle exec ruby #{server_script}, speaking MCP over stdio)"
puts

client = Boukensha::MCP.connect(
  command: ["bundle", "exec", "ruby", server_script],
  dir:     mcp_dir,
  env:     env
)

puts "Discovered #{client.tools.size} tools via tools/list."
puts

def show(client, tool, **args)
  puts "→ #{tool}(#{args})"
  puts "← #{client.call_tool(tool, **args)}"
  puts
end

show(client, "mud_status")
show(client, "look")
show(client, "check", kind: "score")
show(client, "check", kind: "inventory")
show(client, "mud_disconnect")

client.close
puts "done."
