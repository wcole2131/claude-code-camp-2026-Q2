require "minitest/autorun"
$LOAD_PATH.unshift File.expand_path("../lib", __dir__)
require "boukensha/observation/parser"

class TestObservationParser < Minitest::Test
  # Real transcript shape, confirmed live in
  # docs/plans/mud_manager/mcp_integration_verification.md.
  TEMPLE_LOOK = <<~TEXT
    The Temple Of Midgaard
       You are in the southern end of the temple hall in the Temple of
       Midgaard.
       [ Exits: n e s w d ]
    24H 100M 83V (news) (motd) >
  TEXT

  def test_parses_room_name
    result = Boukensha::Observation::Parser.parse(look_text: TEMPLE_LOOK)
    assert_equal "The Temple Of Midgaard", result.room_name
  end

  def test_joins_description_lines
    result = Boukensha::Observation::Parser.parse(look_text: TEMPLE_LOOK)
    assert_equal(
      "You are in the southern end of the temple hall in the Temple of Midgaard.",
      result.description
    )
  end

  def test_parses_exits_from_bracket_line
    result = Boukensha::Observation::Parser.parse(look_text: TEMPLE_LOOK)
    assert_equal %w[n e s w d], result.exits
  end

  def test_strips_the_trailing_status_prompt
    result = Boukensha::Observation::Parser.parse(look_text: TEMPLE_LOOK)
    refute_includes result.description, "100M"
  end

  def test_classifies_mob_presence_lines
    look = <<~TEXT
      By The Temple Altar
         You are standing before a large stone altar.
         A friendly cleric is here.
         [ Exits: n s ]
      23H 100M 82V (news) (motd) >
    TEXT
    result = Boukensha::Observation::Parser.parse(look_text: look)
    assert_equal ["A friendly cleric is here."], result.mobs
    assert_empty result.items
  end

  def test_classifies_item_presence_lines
    look = <<~TEXT
      Market Square
         A bustling square full of vendors.
         A rusty sword is lying here.
         [ Exits: n e s w ]
      24H 100M 83V >
    TEXT
    result = Boukensha::Observation::Parser.parse(look_text: look)
    assert_equal ["A rusty sword is lying here."], result.items
    assert_empty result.mobs
  end

  def test_falls_back_to_supplemental_exits_text_when_look_has_none
    look = "A Dark Room\n   You can't see a thing.\n24H 100M 83V >"
    result = Boukensha::Observation::Parser.parse(look_text: look, exits_text: "Exits: n s")
    assert_equal %w[n s], result.exits
  end

  def test_parse_area_takes_first_meaningful_line
    where = "You are in Midgaard.\n24H 100M 83V (news) (motd) >"
    assert_equal "You are in Midgaard.", Boukensha::Observation::Parser.parse_area(where)
  end

  def test_parse_area_handles_nil
    assert_nil Boukensha::Observation::Parser.parse_area(nil)
  end

  # Confirmed live against the real server -- room name, exits, and item
  # lines all arrive wrapped in real ANSI SGR codes.
  def test_strips_ansi_color_codes_from_room_name_and_exits
    look = "\e[0;33mThe Temple Of Midgaard\e[0m\n" \
           "   You are in the temple hall.\n" \
           "\e[0;36m[ Exits: n e s w d ]\e[0m\n" \
           "24H 100M 83V (news) (motd) >"
    result = Boukensha::Observation::Parser.parse(look_text: look)
    assert_equal "The Temple Of Midgaard", result.room_name
    assert_equal %w[n e s w d], result.exits
  end

  # Confirmed live: `check kind: where` on tbaMUD is a player roster headed
  # "Players in <zone>.", not a "you are in room X" statement.
  def test_parse_area_extracts_zone_from_player_roster_header
    where = "Players in Northern Midgaard\e[0;00m.\r\n--------------------\r\n\r\n24H 100M 83V >"
    assert_equal "Northern Midgaard", Boukensha::Observation::Parser.parse_area(where)
  end
end
