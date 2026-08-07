require "minitest/autorun"
$LOAD_PATH.unshift File.expand_path("../lib", __dir__)
require "boukensha/control/mode"
require "boukensha/control/policy"

class TestControlPolicy < Minitest::Test
  def test_observe_mode_allows_look
    policy = Boukensha::Control::Policy.new
    assert policy.permitted?(Boukensha::Control::Mode::OBSERVE, "look")
  end

  def test_observe_mode_denies_move
    policy = Boukensha::Control::Policy.new
    refute policy.permitted?(Boukensha::Control::Mode::OBSERVE, "move")
  end

  def test_act_mode_denies_send_raw
    policy = Boukensha::Control::Policy.new
    refute policy.permitted?(Boukensha::Control::Mode::ACT, "send_raw")
  end

  def test_act_mode_allows_everything_else
    policy = Boukensha::Control::Policy.new
    assert policy.permitted?(Boukensha::Control::Mode::ACT, "attack")
  end

  def test_unlisted_mode_is_unrestricted
    policy = Boukensha::Control::Policy.new
    assert policy.permitted?(:some_future_mode, "anything")
  end

  def test_enforce_raises_with_a_clear_message
    policy = Boukensha::Control::Policy.new
    error = assert_raises(Boukensha::Control::Policy::NotPermittedError) do
      policy.enforce!(Boukensha::Control::Mode::OBSERVE, "attack")
    end
    assert_match(/attack.*not permitted in :observe mode/, error.message)
  end

  def test_enforce_returns_true_when_permitted
    policy = Boukensha::Control::Policy.new
    assert policy.enforce!(Boukensha::Control::Mode::OBSERVE, "look")
  end
end
