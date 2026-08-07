require "minitest/autorun"
require "tmpdir"
$LOAD_PATH.unshift File.expand_path("../lib", __dir__)
require "boukensha/observation/result"
require "boukensha/memory/world"

class TestMemoryWorld < Minitest::Test
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

  def test_observe_creates_a_node
    world = Boukensha::Memory::World.new
    id = world.observe(temple)
    assert_equal "The Temple Of Midgaard", world.find(id).name
  end

  def test_observe_is_idempotent_on_revisit
    world = Boukensha::Memory::World.new
    id1 = world.observe(temple)
    id2 = world.observe(temple)
    assert_equal id1, id2
    assert_equal 1, world.nodes.size
  end

  def test_observe_wires_reciprocal_edge
    world = Boukensha::Memory::World.new
    temple_id = world.observe(temple)
    altar_id = world.observe(altar, entered_from: temple_id, direction: "n")

    assert_equal altar_id, world.find(temple_id).exits["n"]
    assert_equal temple_id, world.find(altar_id).exits["s"]
  end

  def test_route_returns_empty_array_when_already_there
    world = Boukensha::Memory::World.new
    id = world.observe(temple)
    assert_equal [], world.route(from: id, to: id)
  end

  def test_route_finds_shortest_path
    world = Boukensha::Memory::World.new
    temple_id = world.observe(temple)
    altar_id = world.observe(altar, entered_from: temple_id, direction: "n")

    assert_equal ["s"], world.route(from: altar_id, to: temple_id)
  end

  def test_route_returns_nil_when_unreachable
    world = Boukensha::Memory::World.new
    temple_id = world.observe(temple)
    other = Boukensha::Observation::Result.new(room_name: "Unrelated Room", description: "...", exits: [])
    other_id = world.observe(other)

    assert_nil world.route(from: temple_id, to: other_id)
  end

  def test_identity_by_name_finds_landmark
    world = Boukensha::Memory::World.new
    id = world.observe(temple)
    assert_equal id, world.identity_by_name("The Temple Of Midgaard")
    assert_nil world.identity_by_name("Nowhere")
  end

  def test_dump_and_load_round_trip
    world = Boukensha::Memory::World.new
    temple_id = world.observe(temple)
    world.observe(altar, entered_from: temple_id, direction: "n")

    Dir.mktmpdir do |dir|
      path = File.join(dir, "world.yaml")
      world.dump(path)

      reloaded = Boukensha::Memory::World.load(path)
      assert_equal world.nodes.keys.sort, reloaded.nodes.keys.sort
      assert_equal world.find(temple_id).exits, reloaded.find(temple_id).exits
    end
  end

  def test_load_missing_file_returns_empty_world
    world = Boukensha::Memory::World.load("/nonexistent/path/world.yaml")
    assert_empty world.nodes
  end
end
