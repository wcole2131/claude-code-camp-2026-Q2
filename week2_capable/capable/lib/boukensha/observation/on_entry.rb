require_relative "parser"
require_relative "../control/mode"
require_relative "../control/policy"

module Boukensha
  module Observation
    # The "map where I am, every time I enter" loop -- docs/plans/observable.md
    # goal + decision 6. Decoupled from any specific tool-dispatch mechanism
    # (Registry, MCP client, ...) via `dispatcher`, which just needs to
    # respond to #call(tool_name, **args) and return the tool's raw text
    # reply -- e.g. a lambda wrapping Boukensha::Registry#dispatch.
    module OnEntry
      module_function

      # `character:`/`session_id:` are optional -- the room_visits lifecycle
      # hook (docs/plans/room_database.md decision 5) only fires when both
      # are supplied, so store-less/fixture-only callers (and any World
      # without a `store:`) are unaffected.
      def call(dispatcher:, world:, home_room_name: nil, policy: Control::Policy.new,
                mode: Control::Mode::OBSERVE, entered_from: nil, direction: nil,
                character: nil, session_id: nil)
        look_text  = invoke(dispatcher, policy, mode, "look")
        exits_text = invoke(dispatcher, policy, mode, "check", kind: "exits")
        where_text = invoke(dispatcher, policy, mode, "check", kind: "where")

        result = Parser.parse(look_text: look_text, exits_text: exits_text, where_text: where_text)
        area = Parser.parse_area(where_text)
        identity = world.observe(result, entered_from: entered_from, direction: direction, area: area)

        if character && session_id
          world.record_visit(identity, character: character, session_id: session_id,
                                        entered_from: entered_from, direction: direction)
        end

        route = home_room_name ? world.route_to(from: identity, destination_name: home_room_name) : nil

        {
          result: result,
          identity: identity,
          area: area,
          route_to_home: route,
          directions: render_directions(route)
        }
      end

      def render_directions(route)
        case route
        when nil then "home not yet located on the known map"
        when []  then "already home"
        else "#{route.join(', ')} -- #{route.length} move#{'s' unless route.length == 1} to home"
        end
      end

      def invoke(dispatcher, policy, mode, tool_name, **args)
        policy.enforce!(mode, tool_name)
        dispatcher.call(tool_name, **args)
      end
    end
  end
end
