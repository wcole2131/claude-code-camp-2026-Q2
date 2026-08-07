require "sqlite3"
require "time"

module Boukensha
  module Memory
    # SQLite-backed persistence for Memory::World -- see
    # docs/plans/room_database.md decisions 1-3. `rooms`/`exits` are shared,
    # world-level facts (any character observing the same room describes
    # the same row); `room_visits` is the per-character visit ledger --
    # one row per pass-through, not an aggregate counter, so "how many
    # times has this character passed through room X" stays answerable
    # after the fact.
    class SqliteStore
      SCHEMA = <<~SQL
        CREATE TABLE IF NOT EXISTS rooms (
          id            TEXT PRIMARY KEY,
          name          TEXT NOT NULL,
          description   TEXT NOT NULL,
          area          TEXT,
          first_seen_at TEXT NOT NULL,
          last_seen_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS exits (
          room_id        TEXT NOT NULL REFERENCES rooms(id),
          direction      TEXT NOT NULL,
          destination_id TEXT REFERENCES rooms(id),
          discovered_at  TEXT NOT NULL,
          PRIMARY KEY (room_id, direction)
        );
        CREATE INDEX IF NOT EXISTS exits_by_destination ON exits(destination_id);

        CREATE TABLE IF NOT EXISTS room_visits (
          id           INTEGER PRIMARY KEY AUTOINCREMENT,
          room_id      TEXT NOT NULL REFERENCES rooms(id),
          character    TEXT NOT NULL,
          session_id   TEXT NOT NULL,
          entered_at   TEXT NOT NULL,
          entered_from TEXT REFERENCES rooms(id),
          direction    TEXT
        );
        CREATE INDEX IF NOT EXISTS room_visits_by_room ON room_visits(room_id);
        CREATE INDEX IF NOT EXISTS room_visits_by_character ON room_visits(character, room_id);
      SQL

      def initialize(path)
        @db = SQLite3::Database.new(path)
        @db.execute_batch(SCHEMA)
      end

      # Upserts a room and all of its currently-known exits. Called by
      # World#observe after it updates its own in-memory node -- decision 3
      # ("World keeps its API; SQLite becomes the backing store").
      def persist(id, node)
        now = Time.now.utc.iso8601

        @db.execute(
          "INSERT INTO rooms (id, name, description, area, first_seen_at, last_seen_at) " \
          "VALUES (?, ?, ?, ?, ?, ?) " \
          "ON CONFLICT(id) DO UPDATE SET " \
          "  name = excluded.name, description = excluded.description, " \
          "  area = COALESCE(excluded.area, rooms.area), last_seen_at = excluded.last_seen_at",
          [id, node.name, node.description, node.area, now, now]
        )

        node.exits.each do |direction, destination_id|
          @db.execute(
            "INSERT INTO exits (room_id, direction, destination_id, discovered_at) VALUES (?, ?, ?, ?) " \
            "ON CONFLICT(room_id, direction) DO UPDATE SET " \
            "  destination_id = COALESCE(excluded.destination_id, exits.destination_id)",
            [id, direction, destination_id, now]
          )
        end
      end

      # The lifecycle-hook write: one row per room entry (decision 5). Not
      # called by `persist` itself -- World#record_visit calls this
      # separately, since it needs `character:`/`session_id:` that
      # World#observe's callers don't always have (e.g. store-less tests).
      def record_visit(room_id, character:, session_id:, entered_from: nil, direction: nil)
        @db.execute(
          "INSERT INTO room_visits (room_id, character, session_id, entered_at, entered_from, direction) " \
          "VALUES (?, ?, ?, ?, ?, ?)",
          [room_id, character, session_id, Time.now.utc.iso8601, entered_from, direction]
        )
      end

      # How many times `character` has passed through `room_id` -- the
      # actual answer to "how many times has the player passed through
      # this area." Omit `character:` for the count across all characters.
      def visit_count(room_id, character: nil)
        if character
          @db.get_first_value(
            "SELECT COUNT(*) FROM room_visits WHERE room_id = ? AND character = ?", [room_id, character]
          )
        else
          @db.get_first_value("SELECT COUNT(*) FROM room_visits WHERE room_id = ?", [room_id])
        end
      end

      # Hydrates `world`'s in-memory graph from every known room/exit.
      # Loads the whole table -- see docs/plans/room_database.md's open
      # question on bounding this once a character's known-rooms count
      # grows large; at the stock world's ~1,878-room scale, "load
      # everything" is still cheap.
      def hydrate(world)
        @db.execute("SELECT id, name, description, area FROM rooms").each do |id, name, description, area|
          world.nodes[id] ||= World::Node.new(
            name: name, description: description, exits: {}, mobs: [], items: [], visited_at: nil, area: area
          )
        end

        @db.execute("SELECT room_id, direction, destination_id FROM exits").each do |room_id, direction, destination_id|
          node = world.nodes[room_id]
          node.exits[direction] = destination_id if node
        end

        world
      end

      def close
        @db.close
      end
    end
  end
end
