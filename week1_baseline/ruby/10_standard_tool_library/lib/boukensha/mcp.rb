require "json"
require "open3"

module Boukensha
  # A generic MCP (Model Context Protocol) client over stdio.
  #
  # Connects to *any* MCP server -- not just mud_manager_mcp -- by spawning
  # it as a subprocess and speaking the minimal JSON-RPC 2.0 subset needed
  # for tool calling: initialize, notifications/initialized, tools/list,
  # tools/call. It discovers whatever tools the server advertises at
  # connect time and can register all of them against a Boukensha::Registry
  # generically -- the registry never knows or needs to know the tools came
  # from MCP.
  #
  # Usage:
  #
  #   client = Boukensha::MCP.connect(
  #     command: ["bundle", "exec", "ruby", "bin/mud_manager_server"],
  #     dir:     "../../mud_manager_mcp",
  #     env:     { "MUD_HOST" => "localhost", "MUD_NAME" => "Gandalf", "MUD_PASSWORD" => "secret" }
  #   )
  #   client.register_all(registry)
  #
  # See docs/plans/mud_manager/mcp_generalization_plan.md for the design
  # rationale (why this exists as its own client, separate from any one
  # server it happens to talk to). Mirrored by boukensha/mcp.py
  # (MCPClient) in the Python port -- keep both in sync.
  class MCP
    class Error < StandardError; end

    PROTOCOL_VERSION = "2024-11-05"

    # week1_baseline/, computed from this file's location
    # (lib/boukensha/mcp.rb), for the convenience factory methods below.
    WEEK1_BASELINE_DIR = File.expand_path("../../../..", __dir__)

    def self.connect(command:, dir: nil, env: {})
      new(command: command, dir: dir, env: env).tap(&:connect!)
    end

    # Convenience specs for this repo's three bundled MCP servers, for use
    # with Boukensha.run/repl's mcp_servers:. Raw {command:, dir:, env:}
    # hashes -- nothing about connecting to them is special, these are just
    # shorthand so common cases don't need to spell out a subprocess command
    # by hand. See docs/plans/mud_manager/mcp_mud_plan.md, decision 3.

    def self.file_system_server(working_dir:)
      {
        command: ["bundle", "exec", "ruby", "bin/file_system_mcp_server"],
        dir:     File.join(WEEK1_BASELINE_DIR, "file_system_mcp"),
        env:     { "WORKING_DIR" => File.expand_path(working_dir) }
      }
    end

    def self.shell_server(working_dir:, timeout: 30, allowed_commands: nil)
      env = { "WORKING_DIR" => File.expand_path(working_dir), "SHELL_TIMEOUT" => timeout.to_s }
      env["ALLOWED_COMMANDS"] = allowed_commands.join(",") if allowed_commands

      {
        command: ["bundle", "exec", "ruby", "bin/shell_mcp_server"],
        dir:     File.join(WEEK1_BASELINE_DIR, "shell_mcp"),
        env:     env
      }
    end

    def self.mud_manager_server(name:, password:, host: "localhost", port: 4000)
      {
        command: ["bundle", "exec", "ruby", "bin/mud_manager_server"],
        dir:     File.join(WEEK1_BASELINE_DIR, "mud_manager_mcp"),
        env:     {
          "MUD_HOST"     => host,
          "MUD_PORT"     => port.to_s,
          "MUD_NAME"     => name,
          "MUD_PASSWORD" => password
        }
      }
    end

    def initialize(command:, dir: nil, env: {})
      @command = command
      @dir     = dir
      @env     = env
      @next_id = 0
      @tools   = nil
    end

    def connect!
      # Unset any inherited Bundler env (BUNDLE_GEMFILE, RUBYOPT's
      # -rbundler/setup, etc.) before spawning. Without this, a server
      # spawned via `bundle exec` from *inside* another `bundle exec`
      # process (e.g. the ruby step's own agent launching mud_manager_mcp)
      # inherits the parent's BUNDLE_GEMFILE and resolves against the
      # wrong Gemfile instead of doing a fresh cwd-based lookup in `dir:`.
      #
      # Process.spawn's env hash *merges* with (rather than replaces) the
      # inherited environment -- simply omitting a key from this hash does
      # NOT unset it in the child, only an explicit `nil` value does.
      full_env = ENV.to_h
      full_env.each_key { |k| full_env[k] = nil if k.start_with?("BUNDLE_") || k == "RUBYOPT" }
      full_env.merge!(@env)

      opts = @dir ? { chdir: @dir } : {}
      @stdin, @stdout, @wait_thr = Open3.popen2(full_env, *@command, **opts)

      request("initialize", {
        "protocolVersion" => PROTOCOL_VERSION,
        "capabilities"    => {},
        "clientInfo"      => { "name" => "boukensha", "version" => Boukensha::VERSION }
      })
      notify("notifications/initialized", {})
      self
    end

    # The tool catalog this server advertised, as returned by tools/list:
    # an Array of { "name", "description", "inputSchema" }. Cached after
    # the first call -- a server's tool set isn't expected to change mid
    # connection for anything this repo talks to.
    def tools
      @tools ||= request("tools/list", {})["tools"]
    end

    # Call one tool by name and return its result as a plain String,
    # matching what Boukensha::Registry#dispatch callers already expect.
    def call_tool(name, **args)
      result = request("tools/call", { "name" => name, "arguments" => args })
      content_to_string(result["content"])
    end

    # Register every tool this server advertised against `registry`,
    # generically -- no per-tool code, no knowledge of what the tools do.
    def register_all(registry)
      tools.each do |tool|
        name = tool["name"]
        registry.tool(
          name,
          description: tool["description"],
          parameters:  schema_to_parameters(tool["inputSchema"])
        ) { |**args| call_tool(name, **args) }
      end
    end

    def close
      return if @wait_thr.nil? || !@wait_thr.alive?

      @stdin.close
      @wait_thr.join(5)
    rescue IOError
      nil
    end

    private

    def request(method, params)
      @next_id += 1
      id = @next_id
      @stdin.puts JSON.generate("jsonrpc" => "2.0", "id" => id, "method" => method, "params" => params)
      @stdin.flush

      loop do
        line = @stdout.gets
        raise Error, "#{method}: server closed the connection" unless line

        message = JSON.parse(line)
        next if message["id"] != id

        raise Error, "#{method}: #{message['error']['message']}" if message["error"]
        return message["result"]
      end
    end

    def notify(method, params)
      @stdin.puts JSON.generate("jsonrpc" => "2.0", "method" => method, "params" => params)
      @stdin.flush
    end

    # MUD only ever produces a single "text" block; a generic client can't
    # assume that of every server, so non-text content is rendered as a
    # readable placeholder rather than dropped or raised on.
    def content_to_string(content)
      return "" if content.nil? || content.empty?

      content.map do |block|
        block["type"] == "text" ? block["text"] : "[unsupported content type: #{block['type']}]"
      end.join
    end

    # Inverse of mud_manager_server's input_schema_for -- turns a JSON
    # Schema inputSchema back into the { name: { type:, description:,
    # required: } } shape Boukensha::Registry#tool expects.
    def schema_to_parameters(input_schema)
      return {} unless input_schema

      properties = input_schema["properties"] || {}
      required   = input_schema["required"] || []

      properties.each_with_object({}) do |(name, spec), out|
        entry = { type: spec["type"], description: spec["description"] }
        entry[:required] = false unless required.include?(name)
        out[name.to_sym] = entry
      end
    end
  end
end
