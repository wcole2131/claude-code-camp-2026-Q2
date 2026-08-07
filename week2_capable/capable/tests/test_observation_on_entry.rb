require "minitest/autorun"
require "tmpdir"
$LOAD_PATH.unshift File.expand_path("../lib", __dir__)
require "boukensha/observable"
require "boukensha/memory/sqlite_store"

class FakeDispatcher
  attr_reader :calls

  def initialize(look_text:, where_text: nil)
    @look_text = look_text
    @where_text = where_text
    @calls = []
  end

  def call(tool_name, **args)
    @calls << [tool_name, args]
    case tool_name
    when "look" then @look_text
    when "check" then args[:kind] == "where" ? @where_text.to_s : ""
    else raise "unexpected tool #{tool_name}"
    end
  end
end

class TestObservationOnEntry < Minitest::Test
  TEMPLE_LOOK = <<~TEXT
    The Temple Of Midgaard
       You are in the southern end of the temple hall.
       [ Exits: n e s w d ]
    24H 100M 83V >
  TEXT

  ALTAR_LOOK = <<~TEXT
    By The Temple Altar
       You are standing before a large stone altar.
       [ Exits: n s ]
    23H 100M 82V >
  TEXT

  def test_only_calls_read_only_tools
    dispatcher = FakeDispatcher.new(look_text: TEMPLE_LOOK)
    world = Boukensha::Memory::World.new

    Boukensha::Observation::OnEntry.call(dispatcher: dispatcher, world: world)

    tool_names = dispatcher.calls.map(&:first)
    assert_equal %w[look check check], tool_names
  end

  def test_reports_already_home_at_the_home_room
    dispatcher = FakeDispatcher.new(look_text: TEMPLE_LOOK)
    world = Boukensha::Memory::World.new

    outcome = Boukensha::Observation::OnEntry.call(
      dispatcher: dispatcher, world: world, home_room_name: "The Temple Of Midgaard"
    )

    assert_equal "already home", outcome[:directions]
  end

  def test_reports_home_not_yet_located_before_any_home_visit
    dispatcher = FakeDispatcher.new(look_text: ALTAR_LOOK)
    world = Boukensha::Memory::World.new

    outcome = Boukensha::Observation::OnEntry.call(
      dispatcher: dispatcher, world: world, home_room_name: "The Temple Of Midgaard"
    )

    assert_equal "home not yet located on the known map", outcome[:directions]
  end

  def test_computes_route_after_the_graph_connects_to_home
    world = Boukensha::Memory::World.new

    temple = Boukensha::Observation::OnEntry.call(
      dispatcher: FakeDispatcher.new(look_text: TEMPLE_LOOK),
      world: world,
      home_room_name: "The Temple Of Midgaard"
    )

    at_altar = Boukensha::Observation::OnEntry.call(
      dispatcher: FakeDispatcher.new(look_text: ALTAR_LOOK),
      world: world,
      home_room_name: "The Temple Of Midgaard",
      entered_from: temple[:identity],
      direction: "n"
    )

    assert_equal %w[s], at_altar[:route_to_home]
    assert_equal "s -- 1 move to home", at_altar[:directions]
  end

  def test_updates_the_world_graph
    dispatcher = FakeDispatcher.new(look_text: TEMPLE_LOOK)
    world = Boukensha::Memory::World.new

    outcome = Boukensha::Observation::OnEntry.call(dispatcher: dispatcher, world: world)

    assert_equal "The Temple Of Midgaard", world.find(outcome[:identity]).name
  end

  def test_uses_the_generalized_route_to_for_home_routing
    world = Boukensha::Memory::World.new
    outcome = Boukensha::Observation::OnEntry.call(
      dispatcher: FakeDispatcher.new(look_text: TEMPLE_LOOK), world: world,
      home_room_name: "The Temple Of Midgaard"
    )
    assert_equal [], outcome[:route_to_home]
  end

  def test_records_a_visit_when_character_and_session_id_are_given
    Dir.mktmpdir do |dir|
      store = Boukensha::Memory::SqliteStore.new(File.join(dir, "world.sqlite3"))
      world = Boukensha::Memory::World.new(store: store)
      dispatcher = FakeDispatcher.new(look_text: TEMPLE_LOOK)

      outcome = Boukensha::Observation::OnEntry.call(
        dispatcher: dispatcher, world: world, character: "wanderer", session_id: "s1"
      )
      Boukensha::Observation::OnEntry.call(
        dispatcher: FakeDispatcher.new(look_text: TEMPLE_LOOK), world: world,
        character: "wanderer", session_id: "s2"
      )

      assert_equal 2, store.visit_count(outcome[:identity], character: "wanderer")
    end
  end

  def test_does_not_record_a_visit_without_character_and_session_id
    Dir.mktmpdir do |dir|
      store = Boukensha::Memory::SqliteStore.new(File.join(dir, "world.sqlite3"))
      world = Boukensha::Memory::World.new(store: store)

      outcome = Boukensha::Observation::OnEntry.call(
        dispatcher: FakeDispatcher.new(look_text: TEMPLE_LOOK), world: world
      )

      assert_equal 0, store.visit_count(outcome[:identity])
    end
  end
end
