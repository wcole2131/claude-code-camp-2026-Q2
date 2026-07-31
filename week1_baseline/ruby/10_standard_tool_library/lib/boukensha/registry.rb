require_relative "errors"

module Boukensha
  class Registry
    attr_reader :context

    def initialize(context)
      @context = context
    end

    # All registered Tool structs, by name. Used by Boukensha::MCP::Server
    # to derive tools/list generically, without needing a separate
    # reference to the Context.
    def tools
      @context.tools
    end

    def tool(name, description:, parameters: {}, &block)
      tool = Tool.new(name.to_s, description, parameters, block)
      @context.register_tool(tool)
      tool
    end

    def dispatch(name, args = {})
      tool = @context.tools[name.to_s]
      raise UnknownToolError, "No tool registered as '#{name}'" unless tool
      tool.block.call(**args.transform_keys(&:to_sym))
    end
  end
end