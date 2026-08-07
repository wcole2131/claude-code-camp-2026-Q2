module Boukensha
  module Observation
    # A structured reading of a single MUD room, produced by Parser from raw
    # look/check text. `identity` is the (name, description) pair used by
    # Memory::World for exact-match room recognition -- see
    # docs/plans/observable.md decision 3.
    Result = Struct.new(
      :raw_text, :room_name, :description, :exits, :mobs, :items,
      keyword_init: true
    ) do
      def initialize(*)
        super
        self.exits ||= []
        self.mobs  ||= []
        self.items ||= []
      end

      def identity
        "#{room_name}::#{description}"
      end
    end
  end
end
