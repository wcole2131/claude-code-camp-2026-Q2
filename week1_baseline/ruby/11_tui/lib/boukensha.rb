require_relative "boukensha/version"
require_relative "boukensha/config"
require_relative "boukensha/tasks/player"

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
  def self.run(
    task:,
    system:           nil,
    model:            nil,
    backend:          nil,
    api_key:          nil,
    ollama_host:      "http://localhost:11434",
    log:              nil,
    max_output_tokens: nil,
    working_dir:      Dir.pwd,
    allowed_commands: nil,
    shell_timeout:    30,
    mcp_servers:      nil,
    &block
  )
    cfg           = config                           # loads .env; populates ENV
    task_class    = Tasks::Player
    task_settings = cfg.tasks(task_class.task_name)
    system      ||= task_class.system_prompt(task_settings, user_prompts_dir: cfg.user_prompts_dir, default_prompts_dir: Config::PROMPTS_DIR)
    model       ||= task_class.model(task_settings)
    backend     ||= task_class.provider(task_settings).to_sym
    api_key ||= case backend
                when :anthropic    then ENV["ANTHROPIC_API_KEY"]
                when :openai       then ENV["OPENAI_API_KEY"]
                when :gemini       then ENV["GEMINI_API_KEY"]
                when :ollama_cloud then ENV["OLLAMA_API_KEY"]
                end

    ctx      = Context.new(task: task_class, system: system)
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
    effective_max_iterations = task_class.max_iterations(task_settings)
    effective_max_output_tokens = max_output_tokens || task_class.max_output_tokens(task_settings)
    logger  = Logger.new(log: log, snapshot: {
      task:              task_class.task_name,
      max_iterations:    effective_max_iterations,
      max_output_tokens: effective_max_output_tokens,
      model:             model,
      provider:          backend
    })
    agent   = Agent.new(context: ctx, registry: registry, builder: builder, client: client, logger: logger,
                        task_settings: task_settings, max_iterations: effective_max_iterations, max_output_tokens: effective_max_output_tokens)

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
    max_output_tokens: nil,
    working_dir:      Dir.pwd,
    allowed_commands: nil,
    shell_timeout:    30,
    mcp_servers:      nil,
    tui:              true,
    &block
  )
    cfg           = config                           # loads .env; populates ENV
    task_class    = Tasks::Player
    task_settings = cfg.tasks(task_class.task_name)
    system      ||= task_class.system_prompt(task_settings, user_prompts_dir: cfg.user_prompts_dir, default_prompts_dir: Config::PROMPTS_DIR)
    model       ||= task_class.model(task_settings)
    backend     ||= task_class.provider(task_settings).to_sym
    api_key ||= case backend
                when :anthropic    then ENV["ANTHROPIC_API_KEY"]
                when :openai       then ENV["OPENAI_API_KEY"]
                when :gemini       then ENV["GEMINI_API_KEY"]
                when :ollama_cloud then ENV["OLLAMA_API_KEY"]
                end

    ctx      = Context.new(task: task_class, system: system)
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
    effective_max_iterations = task_class.max_iterations(task_settings)
    effective_max_output_tokens = max_output_tokens || task_class.max_output_tokens(task_settings)
    logger  = Logger.new(log: log, snapshot: {
      task:              task_class.task_name,
      max_iterations:    effective_max_iterations,
      max_output_tokens: effective_max_output_tokens,
      model:             model,
      provider:          backend
    })

    repl = Repl.new(
      context:    ctx,
      registry:   registry,
      builder:    builder,
      client:     client,
      logger:     logger,
      task_settings: task_settings,
      max_iterations:    effective_max_iterations,
      max_output_tokens: effective_max_output_tokens,
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