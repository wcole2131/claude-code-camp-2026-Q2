require_relative "result"

module Boukensha
  module Observation
    # Turns the raw text CircleMUD prints back from `look` (plus optionally
    # `check kind: exits` / `check kind: where`) into a structured Result.
    #
    # Deliberately regex/heuristic, not an LLM call -- see
    # docs/plans/observable.md decision 1. A confirmed real `look` transcript
    # (docs/plans/mud_manager/mcp_integration_verification.md) has this shape:
    #
    #   The Temple Of Midgaard
    #      You are in the southern end of the temple hall in the Temple of
    #      Midgaard.
    #      [ Exits: n e s w d ]
    #   24H 100M 83V (news) (motd) >
    #
    # i.e. room name, then description lines, then an optional bracketed
    # exits line, then a trailing status-bar prompt that `send_cmd` in
    # mud_tools.rb already reads up to but does not strip.
    module Parser
      # CircleMUD sends real ANSI SGR color codes (confirmed live: room
      # names, exits, and item lines all arrive wrapped in e.g. "\e[0;33m"
      # / "\e[0m"). Left in place these break every downstream string match
      # -- room-name identity lookups, exits, presence classification -- so
      # this must run before anything else touches the text.
      ANSI = /\e\[[0-9;]*m/

      EXITS_LINE   = /\[\s*Exits:\s*(?<exits>.*?)\s*\]/i
      PROMPT_LINE  = /\A\s*\d+H\s+\d+M\s+\d+V\b.*>\s*\z/
      PRESENCE_ITEM = /\blying here\b/i
      PRESENCE_MOB  = /\bis (?:here|standing here)\b\.?\z/i
      WHERE_ZONE   = /\APlayers in (?<zone>.+?)\.?\z/i

      module_function

      # look_text is required; exits_text/where_text are optional
      # supplements (e.g. from `check kind: exits` / `check kind: where`)
      # used only when look_text didn't already carry that information.
      def parse(look_text:, exits_text: nil, where_text: nil)
        lines = strip_ansi(look_text).split("\n").map(&:strip)

        room_name = lines.shift.to_s.strip

        description_lines = []
        mobs = []
        items = []
        exits = []

        lines.each do |line|
          next if line.empty?

          if (m = EXITS_LINE.match(line))
            exits = split_exits(m[:exits])
            next
          end

          next if PROMPT_LINE.match?(line)

          if PRESENCE_ITEM.match?(line)
            items << line
          elsif PRESENCE_MOB.match?(line)
            mobs << line
          else
            description_lines << line
          end
        end

        exits = split_exits(extract_exits(exits_text)) if exits.empty? && exits_text

        Result.new(
          raw_text:    look_text,
          room_name:   room_name,
          description: description_lines.join(" "),
          exits:       exits,
          mobs:        mobs,
          items:       items
        )
      end

      # `check kind: where` doesn't report "you are in room X" the way
      # docs/plans/observable.md guessed -- confirmed live, tbaMUD's `where`
      # is a player roster headed "Players in <zone>." (a broad zone name,
      # not the specific room). Extract just the zone name from that
      # header; fall back to the first meaningful line for any other shape.
      def parse_area(where_text)
        return nil if where_text.nil?

        lines = strip_ansi(where_text).split("\n").map(&:strip).reject { |l| l.empty? || PROMPT_LINE.match?(l) }
        return nil if lines.empty?

        (m = WHERE_ZONE.match(lines.first)) ? m[:zone] : lines.first
      end

      def extract_exits(exits_text)
        text = strip_ansi(exits_text)
        m = EXITS_LINE.match(text)
        return m[:exits] if m

        # `check kind: exits` may reply without brackets, e.g. "Exits: n s".
        m2 = /Exits:\s*(?<exits>.*)/i.match(text)
        m2 ? m2[:exits] : ""
      end

      def split_exits(raw)
        raw.to_s.split(/\s+/).map { |d| d.strip.downcase }.reject(&:empty?)
      end

      def strip_ansi(text)
        text.to_s.gsub(ANSI, "")
      end
    end
  end
end
