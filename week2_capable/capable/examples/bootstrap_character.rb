#!/usr/bin/env ruby
# frozen_string_literal: true
#
# One-off utility: walks a brand-new character through tbaMUD's creation
# dialog (name confirmation -> password -> retype -> sex -> class -> press
# return -> main menu -> enter game), landing it in the normal newbie start
# room as an ordinary mortal. Needed because this environment's live server
# had an empty player database -- CircleMUD auto-promotes the *first* ever
# character to Immortal, which is what happened to `dummy` (see
# docs/plans/observable.md's live-wiring notes). This creates a second,
# ordinary character instead of touching that one.
#
# Mapped out by hand against the live server's actual prompt text (not
# assumed from documentation) -- see the raw transcript in conversation
# history for how each prompt was discovered.
#
#   ruby examples/bootstrap_character.rb <name> <password>

require_relative "../../../week0_explore/mud_manager/lib/mud_manager"

name, password = ARGV
abort "usage: bootstrap_character.rb <name> <password>" unless name && password

session = MudManager::Session.new(host: "localhost", port: 4000)
session.open

session.read_until(/By what name do you wish to be known.*\?/i)
session.send_command(name)

response = session.read_until(/Password|Did I get that right/i)
if response =~ /Did I get that right/i
  session.send_command("y")
  response = session.read_until(/Password|already taken/i)
end

if response =~ /already taken/i
  abort "'#{name}' already exists -- pick a different name"
end

session.send_command(password)                       # initial password
session.read_until(/retype password/i)
session.send_command(password)                        # retype
session.read_until(/sex \(M\/F\)/i)
session.send_command("M")
session.read_until(/Select a class/i)
session.send_command("W")                              # Warrior -- matches this repo's existing "Dummy the Swordpupil" convention
session.read_until(/PRESS RETURN/i)
session.send_command(:return)
session.read_until(/Make your choice/i)
session.send_command(1)                                 # enter the game
puts session.read_until_quiet

session.close
puts "\n'#{name}' created and entered the game."
