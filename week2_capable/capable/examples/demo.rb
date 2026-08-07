#!/usr/bin/env ruby
# frozen_string_literal: true
#
# docs/plans/observable.md, phases 1-4, demonstrated end to end against
# fixture text -- no live MUD server needed. The `look` fixtures below
# reproduce the real transcript shape confirmed in
# docs/plans/mud_manager/mcp_integration_verification.md ("The Temple Of
# Midgaard ... [ Exits: n e s w d ] ... 24H 100M 83V (news) (motd) >").
#
#   ruby examples/demo.rb

$LOAD_PATH.unshift File.expand_path("../lib", __dir__)
require "boukensha/observable"

include Boukensha

TEMPLE_LOOK = <<~TEXT
  The Temple Of Midgaard
     You are in the southern end of the temple hall in the Temple of
     Midgaard.
     [ Exits: n e s w d ]
  24H 100M 83V (news) (motd) >
TEXT

ALTAR_LOOK = <<~TEXT
  By The Temple Altar
     You are standing before a large stone altar dedicated to Odin.
     A friendly cleric is here.
     [ Exits: n s ]
  23H 100M 82V (news) (motd) >
TEXT

WHERE_TEXT = "You are in Midgaard.\n24H 100M 83V (news) (motd) >"

# A tiny fake dispatcher standing in for Boukensha::Registry#dispatch --
# see Observation::OnEntry's `dispatcher:` contract. Returns whichever
# fixture is currently "in view"; a real dispatcher would talk to
# mud_manager_mcp instead.
class FakeDispatcher
  def initialize(look_text)
    @look_text = look_text
  end

  def call(tool_name, **args)
    case tool_name
    when "look" then @look_text
    when "check" then args[:kind] == "where" ? WHERE_TEXT : ""
    when "mud_status" then "connected to localhost:4000"
    else raise "FakeDispatcher: unexpected tool #{tool_name.inspect}"
    end
  end
end

world = Memory::World.new
policy = Control::Policy.new

puts "== Entry 1: spawn in the Temple =="
temple = Observation::OnEntry.call(
  dispatcher: FakeDispatcher.new(TEMPLE_LOOK),
  world: world,
  home_room_name: "The Temple Of Midgaard",
  policy: policy
)
puts "room:       #{temple[:result].room_name}"
puts "exits:      #{temple[:result].exits.join(', ')}"
puts "directions: #{temple[:directions]}"
puts

puts "== Entry 2: (agent moved north, under :act mode, elsewhere) =="
altar = Observation::OnEntry.call(
  dispatcher: FakeDispatcher.new(ALTAR_LOOK),
  world: world,
  home_room_name: "The Temple Of Midgaard",
  policy: policy,
  entered_from: temple[:identity],
  direction: "n"
)
puts "room:       #{altar[:result].room_name}"
puts "mobs seen:  #{altar[:result].mobs.join(', ')}"
puts "directions: #{altar[:directions]}"
puts

puts "== Policy in action: :observe mode cannot call move =="
begin
  policy.enforce!(Control::Mode::OBSERVE, "move")
rescue Control::Policy::NotPermittedError => e
  puts "rejected as expected: #{e.message}"
end
