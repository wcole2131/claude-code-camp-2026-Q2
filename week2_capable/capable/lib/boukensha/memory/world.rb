require "yaml"

module Boukensha
  module Memory
    # The persistent room graph -- see docs/plans/observable.md decision 2.
    # Nodes are keyed by Observation::Result#identity ("name::description"),
    # not by name alone, since MUD areas reuse room names (e.g. two
    # "Main Street" rooms in the prototype world.md map). Edges are
    # direction => neighboring identity, nil when the exit is known to exist
    # but hasn't been traversed yet.
    class World
      Node = Struct.new(:name, :description, :exits, :mobs, :items, :visited_at, :area, keyword_init: true)

      # Reciprocal-by-default assumption, corrected later if the MUD proves
      # a given exit isn't actually reciprocal (see decision 2's caveat).
      OPPOSITE = {
        "n" => "s", "s" => "n",
        "e" => "w", "w" => "e",
        "u" => "d", "d" => "u",
        "ne" => "sw", "sw" => "ne",
        "nw" => "se", "se" => "nw"
      }.freeze

      # `store:` is an optional Memory::SqliteStore (or anything responding
      # to #persist/#record_visit) -- see docs/plans/room_database.md
      # decision 3. Store-less (the default) preserves observable.md's
      # original pure-in-memory behavior exactly; no existing caller needs
      # to change.
      def initialize(store: nil)
        @nodes = {}
        @store = store
      end

      attr_reader :nodes

      def opposite(direction)
        OPPOSITE[direction] || direction
      end

      # Records `result` as a node, resolving prior state via exact-match
      # identity (decision 3, step 1). If entered from another known node by
      # traveling `direction`, wires up both the forward and (assumed)
      # reciprocal edge. Persists to `store` (if any) after the in-memory
      # node is updated.
      def observe(result, entered_from: nil, direction: nil, area: nil)
        id = result.identity
        node = @nodes[id] ||= Node.new(name: result.room_name, description: result.description,
                                        exits: {}, mobs: [], items: [], visited_at: nil, area: nil)

        node.mobs = result.mobs
        node.items = result.items
        node.visited_at = Time.now
        node.area = area if area

        result.exits.each { |dir| node.exits[dir] = nil unless node.exits.key?(dir) }

        if entered_from && direction && (from_node = @nodes[entered_from])
          from_node.exits[direction] = id
          node.exits[opposite(direction)] = entered_from
          @store&.persist(entered_from, from_node)
        end

        @store&.persist(id, node)

        id
      end

      # The lifecycle-hook write (decision 5) -- one row per room entry, the
      # actual "how many times has the player passed through here" ledger.
      # No-op without a `store:` (visit tracking is opt-in per Decision 5's
      # framing in observation/on_entry.rb: only recorded when the caller
      # supplies both `character:` and `session_id:`).
      def record_visit(id, character:, session_id:, entered_from: nil, direction: nil)
        @store&.record_visit(id, character: character, session_id: session_id,
                                  entered_from: entered_from, direction: direction)
      end

      def find(identity)
        @nodes[identity]
      end

      # First-visited node with this name -- a landmark lookup (e.g. "The
      # Temple Of Midgaard" for home), not exact-match room identity, since
      # a landmark's exact description isn't known in advance by a caller.
      def identity_by_name(name)
        @nodes.find { |_id, node| node.name == name }&.first
      end

      # The ergonomic destination-routing entry point (decision 4) --
      # `route(from:, to:)` was already generic, this just adds the
      # "resolve a destination by name first" step that was missing.
      def route_to(from:, destination_name:)
        destination = identity_by_name(destination_name)
        return nil unless destination

        route(from: from, to: destination)
      end

      # BFS shortest path from `from` to `to`, both node identities.
      # Returns an array of directions, [] if already there, or nil if `to`
      # isn't reachable from what's been mapped so far (a real, expected
      # state early in a session -- see decision 6).
      def route(from:, to:)
        return [] if from == to
        return nil unless @nodes.key?(from) && @nodes.key?(to)

        queue = [[from, []]]
        seen = { from => true }

        until queue.empty?
          current, path = queue.shift
          node = @nodes[current]

          node.exits.each do |dir, dest|
            next if dest.nil? || seen[dest]

            new_path = path + [dir]
            return new_path if dest == to

            seen[dest] = true
            queue << [dest, new_path]
          end
        end

        nil
      end

      def to_h
        @nodes.transform_values(&:to_h)
      end

      def dump(path)
        File.write(path, YAML.dump(to_h))
      end

      def self.load(path)
        world = new
        return world unless File.exist?(path)

        YAML.load_file(path, permitted_classes: [Time, Symbol]).each do |id, attrs|
          world.nodes[id] = Node.new(**attrs)
        end
        world
      end
    end
  end
end
