#!/usr/bin/env ruby
# frozen_string_literal: true
#
# Extends live_demo.rb: after mapping the spawn room, moves one step (under
# :act mode -- OnEntry itself never calls `move`, matching Control::Policy),
# then runs OnEntry again to prove the full live loop -- parse, graph,
# reciprocal edges, BFS route-to-home -- against a second real room, not
# just the character's spawn point.
#
#   MUD_NAME=wanderer MUD_PASSWORD=helloworld ruby examples/live_walk_demo.rb

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

def report(label, outcome)
  result = outcome[:result]
  puts "== #{label} =="
  puts "room:       #{result.room_name}"
  puts "exits:      #{result.exits.join(', ')}"
  puts "directions: #{outcome[:directions]}"
  puts
end

begin
  dispatcher = MudDispatcher.new(client)
  world = Boukensha::Memory::World.new
  policy = Boukensha::Control::Policy.new

  spawn = Boukensha::Observation::OnEntry.call(
    dispatcher: dispatcher, world: world, home_room_name: "The Temple Of Midgaard", policy: policy
  )
  report("Entry 1: spawn", spawn)

  # move's own parameter schema (mud_tools.rb) wants the full word --
  # "north" not "n" -- unlike look's abbreviated exit list. A move-execution
  # concern, not a parsing one, so it stays local to this demo rather than
  # in the observation/memory library (which never calls move at all).
  DIRECTION_WORD = { "n" => "north", "e" => "east", "s" => "south", "w" => "west", "u" => "up", "d" => "down" }.freeze

  direction = spawn[:result].exits.first
  puts "Moving '#{direction}' (#{DIRECTION_WORD.fetch(direction)}) under :act mode " \
       "(OnEntry itself cannot call move -- policy.enforce! proves it below)..."
  policy.enforce!(Boukensha::Control::Mode::ACT, "move")
  move_result = client.call_tool("move", direction: DIRECTION_WORD.fetch(direction))
  puts "move result: #{move_result.gsub(/\e\[[0-9;]*m/, '').lines.first}"
  puts

  arrived = Boukensha::Observation::OnEntry.call(
    dispatcher: dispatcher, world: world, home_room_name: "The Temple Of Midgaard",
    policy: policy, entered_from: spawn[:identity], direction: direction
  )
  report("Entry 2: after moving #{direction}", arrived)

  puts "Graph now has #{world.nodes.size} known rooms."
ensure
  client.call_tool("mud_disconnect")
  client.close
end
