require "minitest/autorun"
require "tmpdir"
$LOAD_PATH.unshift File.expand_path("../lib", __dir__)
require "boukensha/observation/result"
require "boukensha/memory/world"
require "boukensha/memory/sqlite_store"

class TestMemorySqliteStore < Minitest::Test
  def temple
    Boukensha::Observation::Result.new(
      room_name: "The Temple Of Midgaard",
      description: "You are in the southern end of the temple hall.",
      exits: %w[n e s w d]
    )
  end

  def altar
    Boukensha::Observation::Result.new(
      room_name: "By The Temple Altar",
      description: "You are standing before a large stone altar.",
      exits: %w[n s]
    )
  end

  def with_store
    Dir.mktmpdir do |dir|
      yield Boukensha::Memory::SqliteStore.new(File.join(dir, "world.sqlite3"))
    end
  end

  def test_persist_writes_a_queryable_room_row
    with_store do |store|
      world = Boukensha::Memory::World.new(store: store)
      id = world.observe(temple, area: "Northern Midgaard")

      row = store.instance_variable_get(:@db).execute("SELECT name, area FROM rooms WHERE id = ?", [id]).first
      assert_equal ["The Temple Of Midgaard", "Northern Midgaard"], row
    end
  end

  def test_persist_writes_exit_rows
    with_store do |store|
      world = Boukensha::Memory::World.new(store: store)
      temple_id = world.observe(temple)
      altar_id = world.observe(altar, entered_from: temple_id, direction: "n")

      dest = store.instance_variable_get(:@db).get_first_value(
        "SELECT destination_id FROM exits WHERE room_id = ? AND direction = ?", [temple_id, "n"]
      )
      assert_equal altar_id, dest
    end
  end

  def test_record_visit_and_visit_count
    with_store do |store|
      world = Boukensha::Memory::World.new(store: store)
      id = world.observe(temple)

      world.record_visit(id, character: "wanderer", session_id: "s1")
      world.record_visit(id, character: "wanderer", session_id: "s2")
      world.record_visit(id, character: "someone_else", session_id: "s3")

      assert_equal 2, store.visit_count(id, character: "wanderer")
      assert_equal 3, store.visit_count(id)
    end
  end

  def test_record_visit_without_store_is_a_safe_noop
    world = Boukensha::Memory::World.new
    id = world.observe(temple)
    world.record_visit(id, character: "wanderer", session_id: "s1")
  end

  def test_hydrate_rebuilds_the_graph_including_exits
    with_store do |store|
      writer = Boukensha::Memory::World.new(store: store)
      temple_id = writer.observe(temple)
      writer.observe(altar, entered_from: temple_id, direction: "n")

      reader = Boukensha::Memory::World.new(store: store)
      store.hydrate(reader)

      assert_equal "The Temple Of Midgaard", reader.find(temple_id).name
      assert_equal writer.nodes[temple_id].exits, reader.find(temple_id).exits
    end
  end

  def test_persist_is_idempotent_across_repeated_observations
    with_store do |store|
      world = Boukensha::Memory::World.new(store: store)
      world.observe(temple)
      world.observe(temple)

      count = store.instance_variable_get(:@db).get_first_value("SELECT COUNT(*) FROM rooms")
      assert_equal 1, count
    end
  end
end
