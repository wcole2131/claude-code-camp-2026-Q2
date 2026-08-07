#!/usr/bin/env ruby
# frozen_string_literal: true
#
# docs/plans/room_database.md phase 4 live verification: walks spawn -> move
# -> arrive (live_walk_demo.rb's sequence) TWICE in a row against a real
# tbaMUD server, through a persistent Memory::SqliteStore, then queries
# room_visits directly to confirm each room's visit count reads 2 -- the
# actual "how many times has the player passed through here" feature,
# proven against the real database, not asserted from a unit test alone.
#
#   MUD_NAME=wanderer MUD_PASSWORD=helloworld ruby examples/live_sqlite_demo.rb

require "yaml"
require "securerandom"

RUBY_STEP_LIB = File.expand_path("../../../week1_baseline/ruby/12_context/lib", __dir__)
$LOAD_PATH.unshift RUBY_STEP_LIB
$LOAD_PATH.unshift File.expand_path("../lib", __dir__)

require "boukensha/version"
require "boukensha/mcp"
require "boukensha/observable"
require "boukensha/memory/sqlite_store"

class MudDispatcher
  def initialize(client)
    @client = client
  end

  def call(tool_name, **args)
    @client.call_tool(tool_name, **args)
  end
end

DIRECTION_WORD = { "n" => "north", "e" => "east", "s" => "south", "w" => "west", "u" => "up", "d" => "down" }.freeze

def walk_once(client, dispatcher, world, policy, character:, session_id:)
  spawn = Boukensha::Observation::OnEntry.call(
    dispatcher: dispatcher, world: world, home_room_name: "The Temple Of Midgaard",
    policy: policy, character: character, session_id: session_id
  )

  direction = spawn[:result].exits.first
  policy.enforce!(Boukensha::Control::Mode::ACT, "move")
  client.call_tool("move", direction: DIRECTION_WORD.fetch(direction))

  arrived = Boukensha::Observation::OnEntry.call(
    dispatcher: dispatcher, world: world, home_room_name: "The Temple Of Midgaard",
    policy: policy, entered_from: spawn[:identity], direction: direction,
    character: character, session_id: session_id
  )

  # Walk back via the known reciprocal direction, not route_to_home --
  # this must work regardless of where the character actually started
  # (its live position persists between separate script runs; it need not
  # be sitting at "home" when this script happens to start), so the next
  # pass reliably revisits the same two rooms rather than wandering
  # further each time.
  back_direction = world.opposite(direction)
  policy.enforce!(Boukensha::Control::Mode::ACT, "move")
  client.call_tool("move", direction: DIRECTION_WORD.fetch(back_direction))

  [spawn[:identity], arrived[:identity]]
end

settings_path = File.expand_path("../../../.boukensha/settings.yaml", __dir__)
mud = YAML.load_file(settings_path).fetch("mud")
mud = mud.merge(
  "username" => ENV.fetch("MUD_NAME", mud["username"]),
  "password" => ENV.fetch("MUD_PASSWORD", mud["password"])
)
character = mud.fetch("username")

db_path = File.expand_path("../../../.boukensha/world.sqlite3", __dir__)
puts "SQLite store: #{db_path}"
store = Boukensha::Memory::SqliteStore.new(db_path)

puts "Connecting to #{mud.fetch('host')}:#{mud.fetch('port')} as #{character}..."
client = Boukensha::MCP.connect(
  **Boukensha::MCP.mud_manager_server(
    name: character, password: mud.fetch("password"), host: mud.fetch("host"), port: mud.fetch("port")
  )
)

begin
  dispatcher = MudDispatcher.new(client)
  world = Boukensha::Memory::World.new(store: store)
  store.hydrate(world)
  policy = Boukensha::Control::Policy.new

  spawn_id = arrived_id = nil
  2.times do |i|
    session_id = "#{Time.now.utc.strftime('%Y%m%dT%H%M%SZ')}-#{SecureRandom.hex(4)}"
    puts "-- pass #{i + 1}, session #{session_id} --"
    spawn_id, arrived_id = walk_once(client, dispatcher, world, policy, character: character, session_id: session_id)
  end

  puts
  puts "spawn room visits (#{character}):   #{store.visit_count(spawn_id, character: character)}"
  puts "second room visits (#{character}):  #{store.visit_count(arrived_id, character: character)}"
ensure
  client.call_tool("mud_disconnect")
  client.close
  store.close
end
