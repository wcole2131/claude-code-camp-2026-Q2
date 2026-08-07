#!/usr/bin/env ruby
# frozen_string_literal: true
#
# Wires Observation::OnEntry to the real mud_manager_mcp server -- a live
# CircleMUD connection -- instead of examples/demo.rb's FakeDispatcher.
# Read-only and safe to run against a live character: OnEntry only ever
# calls look/check under :observe mode, structurally enforced by
# Control::Policy (see lib/boukensha/observation/on_entry.rb).
#
# Reuses Boukensha::MCP (week1_baseline/ruby/12_context/lib/boukensha/mcp.rb)
# as the client -- no new MCP protocol code needed here, just an adapter
# from its #call_tool(name, **args) to the #call(name, **args) contract
# Observation::OnEntry's `dispatcher:` expects.
#
#   ruby examples/live_demo.rb

require "yaml"

RUBY_STEP_LIB = File.expand_path("../../../week1_baseline/ruby/12_context/lib", __dir__)
$LOAD_PATH.unshift RUBY_STEP_LIB
$LOAD_PATH.unshift File.expand_path("../lib", __dir__)

require "boukensha/version"
require "boukensha/mcp"
require "boukensha/observable"

class MudDispatcher
  def initialize(client)
    @client = client
  end

  def call(tool_name, **args)
    @client.call_tool(tool_name, **args)
  end
end

settings_path = File.expand_path("../../../.boukensha/settings.yaml", __dir__)
mud = YAML.load_file(settings_path).fetch("mud")
mud = mud.merge(
  "username" => ENV.fetch("MUD_NAME", mud["username"]),
  "password" => ENV.fetch("MUD_PASSWORD", mud["password"])
)

puts "Connecting to #{mud.fetch('host')}:#{mud.fetch('port')} as #{mud.fetch('username')}..."

client = Boukensha::MCP.connect(
  **Boukensha::MCP.mud_manager_server(
    name:     mud.fetch("username"),
    password: mud.fetch("password"),
    host:     mud.fetch("host"),
    port:     mud.fetch("port")
  )
)

begin
  dispatcher = MudDispatcher.new(client)
  world = Boukensha::Memory::World.new

  outcome = Boukensha::Observation::OnEntry.call(
    dispatcher: dispatcher,
    world: world,
    home_room_name: "The Temple Of Midgaard"
  )

  result = outcome[:result]
  puts
  puts "room:        #{result.room_name}"
  puts "description: #{result.description}"
  puts "exits:       #{result.exits.join(', ')}"
  puts "mobs:        #{result.mobs.empty? ? '(none)' : result.mobs.join(', ')}"
  puts "items:       #{result.items.empty? ? '(none)' : result.items.join(', ')}"
  puts "area:        #{outcome[:area] || '(unknown)'}"
  puts "directions:  #{outcome[:directions]}"
  puts
  puts "raw look text:"
  puts result.raw_text
ensure
  client.call_tool("mud_disconnect")
  client.close
end
