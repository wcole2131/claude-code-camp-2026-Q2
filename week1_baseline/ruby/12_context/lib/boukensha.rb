require_relative "boukensha/version"
require_relative "boukensha/config"

module Boukensha
  @debug  = false
  @config = nil

  def self.config
    @config ||= Config.new
  end

  def self.debug!
    @debug = true
  end

  def self.debug?
    @debug
  end

  # One-shot run: send a single task, get a response, return.
  #
  # mcp_servers:      Array of {command:, dir:, env:} specs -- every tool the
  #                   agent has comes from connecting to these MCP servers via
  #                   Boukensha::MCP and discovering their tools/list. The
  #                   framework itself has no built-in tools (see
  #                   docs/plans/mud_manager/mcp_mud_plan.md). nil (default)
  #                   builds a sensible default set from working_dir:/mud
  #                   config, below; pass [] to connect to nothing, or your
  #                   own list to take full control. Boukensha::MCP.file_system_server,
  #                   .shell_server, and .mud_manager_server build the specs
  #                   for this repo's three bundled servers.
  #
  # working_dir:      only used to build the default mcp_servers: (file_system_mcp
  #                   and shell_mcp point at this directory). Ignored if
  #                   mcp_servers: is given explicitly. Pass working_dir: false
  #                   to exclude both from the default set.
  #
  # allowed_commands: only used to build the default shell_mcp spec (see above).
  #
  # shell_timeout:    only used to build the default shell_mcp spec (see above).
  #
  # context_window:   the model's maximum input token capacity. nil (default)
  #                   looks it up from the configured model via Boukensha::Models.
  def self.run(
    task:,
    system:           nil,
    model:            nil,
    backend:          nil,
    api_key:          nil,
    ollama_host:      "http://localhost:11434",
    log:              nil,
    context_window:   nil,
    max_output_tokens: nil,
    working_dir:      Dir.pwd,
    allowed_commands: nil,
    shell_timeout:    30,
    mcp_servers:      nil,
    &block
  )
    cfg     = config                           # loads .env; populates ENV
    system  ||= cfg.system_prompt
    model   ||= cfg.model
    context_window ||= Models.context_window(model)
    backend ||= cfg.provider_type.to_sym
    api_key ||= case backend
                when :anthropic    then ENV["ANTHROPIC_API_KEY"]
                when :openai       then ENV["OPENAI_API_KEY"]
                when :gemini       then ENV["GEMINI_API_KEY"]
                when :ollama_cloud then ENV["OLLAMA_API_KEY"]
                end

    ctx      = Context.new(system: system, context_window: context_window, working_dir: working_dir, compaction_threshold: cfg.agent_compaction_threshold)
    registry = Registry.new(ctx)

    resolved_servers = mcp_servers || default_mcp_servers(
      cfg, working_dir: working_dir, allowed_commands: allowed_commands, shell_timeout: shell_timeout
    )
    mcp_clients = connect_mcp_servers(registry, resolved_servers)

    RunDSL.new(registry).instance_eval(&block) if block

    be = case backend
         when :anthropic    then Backends::Anthropic.new(api_key: api_key, model: model)
         when :openai       then Backends::OpenAI.new(api_key: api_key, model: model)
         when :gemini       then Backends::Gemini.new(api_key: api_key, model: model)
         when :ollama       then Backends::Ollama.new(host: ollama_host, model: model)
         when :ollama_cloud then Backends::OllamaCloud.new(api_key: api_key, model: model)
         else raise ArgumentError, "Unknown backend #{backend.inspect}. Use :anthropic, :openai, :gemini, :ollama, or :ollama_cloud."
         end

    builder = PromptBuilder.new(ctx, be)
    client  = Client.new(builder)
    logger  = Logger.new(log: log, snapshot: {
      max_iterations:    cfg.agent_max_iterations,
      max_turn_tokens:   cfg.agent_max_turn_tokens,
      max_output_tokens: (max_output_tokens || cfg.agent_max_output_tokens),
      context_window:    context_window,
      model:             model,
      provider:          backend
    })
    agent   = Agent.new(context: ctx, registry: registry, builder: builder, client: client, logger: logger,
                        max_iterations: cfg.agent_max_iterations,
                        max_turn_tokens: cfg.agent_max_turn_tokens,
                        max_output_tokens: (max_output_tokens || cfg.agent_max_output_tokens))

    ctx.add_message(:user, task)
    agent.run
  ensure
    mcp_clients&.each(&:close)
    logger&.close
  end

  # Interactive REPL — see Boukensha.run for full option documentation.
  #
  # tui: true (default) wraps the REPL in a charm-ruby TUI.  Pass tui: false or
  # use the --no-tui CLI flag to fall back to the plain terminal REPL.
  def self.repl(
    system:           nil,
    model:            nil,
    backend:          nil,
    api_key:          nil,
    ollama_host:      "http://localhost:11434",
    log:              nil,
    context_window:   nil,
    max_output_tokens: nil,
    working_dir:      Dir.pwd,
    allowed_commands: nil,
    shell_timeout:    30,
    mcp_servers:      nil,
    tui:              true,
    &block
  )
    cfg     = config                           # loads .env; populates ENV
    system  ||= cfg.system_prompt
    model   ||= cfg.model
    context_window ||= Models.context_window(model)
    backend ||= cfg.provider_type.to_sym
    api_key ||= case backend
                when :anthropic    then ENV["ANTHROPIC_API_KEY"]
                when :openai       then ENV["OPENAI_API_KEY"]
                when :gemini       then ENV["GEMINI_API_KEY"]
                when :ollama_cloud then ENV["OLLAMA_API_KEY"]
                end

    ctx      = Context.new(system: system, context_window: context_window, working_dir: working_dir, compaction_threshold: cfg.agent_compaction_threshold)
    registry = Registry.new(ctx)

    resolved_servers = mcp_servers || default_mcp_servers(
      cfg, working_dir: working_dir, allowed_commands: allowed_commands, shell_timeout: shell_timeout
    )
    mcp_clients = connect_mcp_servers(registry, resolved_servers)

    RunDSL.new(registry).instance_eval(&block) if block

    be = case backend
         when :anthropic    then Backends::Anthropic.new(api_key: api_key, model: model)
         when :openai       then Backends::OpenAI.new(api_key: api_key, model: model)
         when :gemini       then Backends::Gemini.new(api_key: api_key, model: model)
         when :ollama       then Backends::Ollama.new(host: ollama_host, model: model)
         when :ollama_cloud then Backends::OllamaCloud.new(api_key: api_key, model: model)
         else raise ArgumentError, "Unknown backend #{backend.inspect}. Use :anthropic, :openai, :gemini, :ollama, or :ollama_cloud."
         end

    builder = PromptBuilder.new(ctx, be)
    client  = Client.new(builder)
    logger  = Logger.new(log: log, snapshot: {
      max_iterations:    cfg.agent_max_iterations,
      max_turn_tokens:   cfg.agent_max_turn_tokens,
      max_output_tokens: (max_output_tokens || cfg.agent_max_output_tokens),
      context_window:    context_window,
      model:             model,
      provider:          backend
    })

    repl = Repl.new(
      context:    ctx,
      registry:   registry,
      builder:    builder,
      client:     client,
      logger:     logger,
      max_iterations:    cfg.agent_max_iterations,
      max_turn_tokens:   cfg.agent_max_turn_tokens,
      max_output_tokens: (max_output_tokens || cfg.agent_max_output_tokens),
      config_dir: cfg.dir,
      provider:   backend,
      model:      model,
      version:    VERSION,
      api_key:    api_key
    )

    if tui && defined?(Tui)
      Tui.new(repl).start
    else
      repl.start
    end
  rescue Interrupt
    puts "\nInterrupted."
  ensure
    mcp_clients&.each(&:close)
    logger&.close
  end

  # Connect to every MCP server spec ({command:, dir:, env:}) and register
  # every tool each one advertises against `registry`, generically. Returns
  # the connected Boukensha::MCP clients so callers can close them later.
  def self.connect_mcp_servers(registry, specs)
    specs.map do |spec|
      client = MCP.connect(command: spec.fetch(:command), dir: spec[:dir], env: spec[:env] || {})
      client.register_all(registry)
      client
    end
  end
  private_class_method :connect_mcp_servers

  # Build the default mcp_servers: list used when Boukensha.run/repl aren't
  # given one explicitly: file_system_mcp + shell_mcp rooted at working_dir
  # (skipped entirely if working_dir: false), plus mud_manager_mcp if
  # settings.yaml's mud: block has a username configured.
  def self.default_mcp_servers(cfg, working_dir:, allowed_commands:, shell_timeout:)
    servers = []

    if working_dir
      servers << MCP.file_system_server(working_dir: working_dir)
      servers << MCP.shell_server(working_dir: working_dir, timeout: shell_timeout, allowed_commands: allowed_commands)
    end

    if cfg.mud_host && cfg.mud_username
      servers << MCP.mud_manager_server(
        host: cfg.mud_host, port: cfg.mud_port, name: cfg.mud_username, password: cfg.mud_password
      )
    end

    servers
  end
  private_class_method :default_mcp_servers
end

require_relative "boukensha/tool"
require_relative "boukensha/mcp"
require_relative "boukensha/mcp/server"
require_relative "boukensha/message"
require_relative "boukensha/models"
require_relative "boukensha/context"
require_relative "boukensha/errors"
require_relative "boukensha/registry"
require_relative "boukensha/prompt_builder"
require_relative "boukensha/logger"
require_relative "boukensha/backends/base"
require_relative "boukensha/backends/anthropic"
require_relative "boukensha/backends/gemini"
require_relative "boukensha/backends/ollama"
require_relative "boukensha/backends/ollama_cloud"
require_relative "boukensha/backends/openai"
require_relative "boukensha/client"
require_relative "boukensha/agent"
require_relative "boukensha/run_dsl"
require_relative "boukensha/repl"
require_relative "boukensha/tui"