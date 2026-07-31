require_relative "../mcp"
require "json"

module Boukensha
  class MCP
    # A generic MCP (Model Context Protocol) server over stdio. Mirrors
    # Boukensha::MCP (the client) on the serving side: takes a Registry —
    # any Registry, with any tools registered against it — and serves
    # initialize/notifications/initialized/tools/list/tools/call generically.
    #
    # This is the piece that used to be hand-rolled once per server script
    # (mud_manager_mcp/bin/mud_manager_server). Every MCP server in this repo
    # (mud_manager_mcp, file_system_mcp, shell_mcp) now shares this instead of
    # each re-implementing the same JSON-RPC loop:
    #
    #   ctx      = Boukensha::Context.new(task: nil)
    #   registry = Boukensha::Registry.new(ctx)
    #   MyTools.register(registry, ...)
    #   Boukensha::MCP::Server.new(registry, name: "my_server").serve
    #
    # See docs/plans/mud_manager/mcp_mud_plan.md for why.
    class Server
      def initialize(registry, name:, version: "0.1.0")
        @registry = registry
        @name     = name
        @version  = version
      end

      def serve
        STDOUT.sync = true
        STDIN.each_line do |line|
          line = line.strip
          next if line.empty?

          handle(line)
        end
      end

      private

      def handle(line)
        begin
          message = JSON.parse(line)
        rescue JSON::ParserError => e
          respond_error(nil, -32_700, "Parse error: #{e.message}")
          return
        end

        id     = message["id"]
        method = message["method"]
        params = message["params"] || {}

        case method
        when "initialize"
          respond(id, {
            "protocolVersion" => PROTOCOL_VERSION,
            "capabilities"    => { "tools" => {} },
            "serverInfo"      => { "name" => @name, "version" => @version }
          })
        when "notifications/initialized"
          # Notification -- no id, no response expected.
        when "tools/list"
          respond(id, { "tools" => tools_list })
        when "tools/call"
          handle_tools_call(id, params)
        else
          respond_error(id, -32_601, "Method not found: #{method}") if id
        end
      end

      def tools_list
        @registry.tools.values.map do |tool|
          {
            "name"        => tool.name,
            "description" => tool.description,
            "inputSchema" => input_schema_for(tool.parameters)
          }
        end
      end

      def handle_tools_call(id, params)
        result = @registry.dispatch(params.fetch("name"), params["arguments"] || {})
        respond(id, { "content" => text_content(result), "isError" => false })
      rescue KeyError => e
        respond_error(id, -32_602, "Invalid params: #{e.message}")
      rescue Boukensha::UnknownToolError => e
        respond_error(id, -32_602, e.message)
      rescue StandardError => e
        # An unexpected crash *during* tool execution (not a malformed
        # request) is a tool-level failure, not a protocol-level one.
        respond(id, { "content" => text_content("#{e.class}: #{e.message}"), "isError" => true })
      end

      # Convert a Boukensha parameters hash ({ name: { type:, description:,
      # required: } }) into a JSON Schema `inputSchema` object. `required:`
      # defaults to true.
      def input_schema_for(parameters)
        properties = {}
        required   = []

        parameters.each do |name, spec|
          properties[name.to_s] = { "type" => spec[:type], "description" => spec[:description] }.compact
          required << name.to_s if spec.fetch(:required, true)
        end

        { "type" => "object", "properties" => properties, "required" => required }
      end

      def text_content(str)
        [{ "type" => "text", "text" => str }]
      end

      def respond(id, result)
        puts JSON.generate("jsonrpc" => "2.0", "id" => id, "result" => result)
      end

      def respond_error(id, code, message)
        puts JSON.generate("jsonrpc" => "2.0", "id" => id, "error" => { "code" => code, "message" => message })
      end
    end
  end
end
