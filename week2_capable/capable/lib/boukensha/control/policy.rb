require_relative "mode"

module Boukensha
  module Control
    # Gates which tools a given Mode is allowed to call -- see
    # docs/plans/observable.md decision 5. A rule with `allow:` is a
    # whitelist (only those tools are permitted); a rule with `deny:` is a
    # blacklist (everything except those tools is permitted). A mode with no
    # rule entry at all is unrestricted.
    class Policy
      class NotPermittedError < StandardError; end

      DEFAULT_RULES = {
        Mode::OBSERVE => { allow: %w[look examine check mud_status] },
        Mode::ACT     => { deny: %w[send_raw] }
      }.freeze

      def initialize(rules = DEFAULT_RULES)
        @rules = rules
      end

      def permitted?(mode, tool_name)
        rule = @rules[mode]
        return true unless rule

        name = tool_name.to_s
        if rule[:allow]
          rule[:allow].include?(name)
        elsif rule[:deny]
          !rule[:deny].include?(name)
        else
          true
        end
      end

      # Raises rather than silently no-opping so the caller (and, one day,
      # the reflector) learns from the rejection instead of being confused
      # by nothing happening -- decision 5's explicit choice.
      def enforce!(mode, tool_name)
        return true if permitted?(mode, tool_name)

        raise NotPermittedError, "tool '#{tool_name}' not permitted in :#{mode} mode"
      end
    end
  end
end
