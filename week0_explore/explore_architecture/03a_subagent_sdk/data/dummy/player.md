# Player Memory -- Dummy

Last updated: 2026-07-20 (session 4 - walked to Guild of Swordsmen)

## Status
- Level: 1
- Class/Title: Dummy the Swordpupil (Warrior)
- Exp / Exp to next level: 192 / 1848 needed (36 from crawler, 156 from newbie monster)
- Gold: 10 (found in newbie zone)
- HP / Mana / Move (max): 23H / 100M / 82V (fresh session, near full)
- Current location: The Tournament And Practice Yard (Guild of Swordsmen practice yard, guildmaster present)

## Long-Term Goals
- [ ] Reach level 7
- [ ] Defeat: Massive Minotaur (newbie zone north of Midgaard) -- formidable
      challenge for a level 7 character, excellent target goal

## Progress Log
(most recent entry first -- one line per notable event: level-ups, deaths, goal
progress, key decisions. Not a transcript of every command.)
- 2026-07-20 (session 4): Errand -- walked from Temple of Midgaard to the
  Guild of Swordsmen practice yard to stand near the guildmaster (no fighting/
  grinding this session). Route confirmed working end-to-end: Temple Of
  Midgaard -> s (Temple Square) -> s (Market Square) -> e (Main Street,
  general store/pet shop) -> e (Main Street, weapon shop/Guild entrance) ->
  s (Entrance Hall To The Guild Of Swordsmen) -> e (The Bar Of Swordsmen) ->
  s (The Tournament And Practice Yard). 7 moves total from the temple. Ended
  session standing in the practice yard with the guildmaster; character left
  there, session not stopped.
- 2026-07-20 (session 3): Fixed a stale-path bug in scripts/mud_env.sh (data
  dir was resolving wrong). Found old session dead ("Multiple login detected
  -- disconnecting"), stopped and restarted cleanly. Login now drops the
  character one room further out than expected -- at "Behind The Temple
  Altar" (dirt path, exits n/s) rather than directly in the temple. Walked
  south twice (Behind The Temple Altar -> By The Temple Altar -> The Temple
  Of Midgaard) to get back to the start room. No stat loss from the earlier
  disconnect.
- 2026-07-17 (session 2, continued): Started grinding in newbie zone. Defeated
  creepy crawler (+36 exp) and newbie monster (+156 exp, long fight ~2-3 min 
  bare-handed). Found 10 gold coins. Healed at Grunting Boar Inn. Combat is
  very slow without weapons - need to get weapon from shop to speed up grinding.
  Currently hunting toward level 7. Target: Red Room (Minotaur location, per user hint).
- 2026-07-17 (session 1): Found the Guild of Swordsmen (starting/warrior guild) and its
  guildmaster in the practice yard. Tried `practice kick` -- failed with
  "You do not seem to be able to practice now." because of 0 practice
  sessions remaining. Need to gain exp/level up to earn more sessions.

## Known Skills
- kick (bad) -- known but low proficiency, 0 practice sessions available to improve it right now

## Inventory / Equipment
- 10 gold coins (found in newbie zone, can buy weapon)

## Strategy Notes
- Level 1 combat is VERY slow: Creepy crawler took ~2 min to kill, newbie 
  monster fights are grinding matches with light damage per round. Need to 
  find better weapons/equipment to speed up combat, or higher level to access
  easier mobs.
- Healing: Grunting Boar Inn fully restores HP just by visiting reception 
  area (very fast respawn at inn location).
- Found gold coins lying on ground in Beginning Of Passage - can pick up for
  buying equipment.
- Natural HP/Mana regeneration occurs while in combat, helping with long fights.
