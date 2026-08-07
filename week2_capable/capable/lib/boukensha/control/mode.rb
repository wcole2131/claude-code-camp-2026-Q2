module Boukensha
  module Control
    # See docs/plans/observable.md decision 5. :observe is the read-only
    # mode the automatic on-entry mapping step runs under; :act is
    # goal-directed play under the planner's control.
    module Mode
      OBSERVE = :observe
      ACT = :act

      ALL = [OBSERVE, ACT].freeze

      def self.valid?(mode)
        ALL.include?(mode)
      end
    end
  end
end
