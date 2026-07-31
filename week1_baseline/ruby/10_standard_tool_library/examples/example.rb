#!/usr/bin/env ruby
# frozen_string_literal: true
#
# Step 10 — A Standard Tool Library (MUD demo)
#
# Demonstrates connecting to mud_manager_mcp (week1_baseline/mud_manager_mcp),
# a real MCP server, via Boukensha's default mcp_servers: wiring -- no MUD
# tool implementation lives in this framework itself (see
# docs/plans/mud_manager/mcp_mud_plan.md). Connection credentials come from
# ~/.boukensha/settings.yaml (mud: host/port/username/password) by default.
# Set BOUKENSHA_DIR to point at a different config directory.
#
# You can still override individual values as keyword arguments:
#
#   ruby examples/demo.rb
#   BOUKENSHA_DIR=iterations/.boukensha ruby examples/demo.rb

ENV["BOUKENSHA_DIR"] ||= File.expand_path("../../../../.boukensha", __dir__)

$LOAD_PATH.unshift File.expand_path("../lib", __dir__)
require "boukensha"

cfg = Boukensha.config
puts "Config: #{cfg}"
puts "API key set? #{!ENV['ANTHROPIC_API_KEY'].nil?}"
puts

result = Boukensha.run(
  task: "Connect to the MUD, look at your surroundings, check your score, " \
        "then look at the available exits and tell me what you see.",
  # system/model/api_key all come from config automatically
  working_dir: false   # no filesystem_mcp/shell_mcp needed for MUD play
  # mcp_servers: defaults to [mud_manager_server(...)] since settings.yaml's
  # mud: block is configured (see Boukensha.default_mcp_servers)
)

puts result
