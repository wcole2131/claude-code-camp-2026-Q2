# Preweek Technical Documentation

## Technical Goal
For this week, work on getting baseline agents configured to allow the boukensha application to access the 
MUD application with the default user in order to play the game.

## Technical Uncertainty
- I'm not sure if creating the Python enjoinment will work when copying the delta from the Ruby directories
- Will the boukensha be able to work with two different programming language?
- How does porting from one language to another work and how much configuration is needed to resolve any issues.

## Technical Hypotheses
I need to verify that the mud-manager that was created in week0 will be able to connect to a mcp server to allow the
boukensha application will be able to access the tbaMUD server and access the game with the user's that were created.

## Technical Observations
- Their was constant redundancy with updating the ruby gem files when adding the new agents for ruby and python.
- I'm unaware of how the MCP will connect to the MUD application and what files will need to be configured.
- I wasn't sure how the logger was going to connect to boukensha to gather the information of the player.

## Technical Conclusions
This process was very intense with setting up all the agent directories and getting the MCP server configured for the 
boukensha application.
The MCP agent setup was causing me problems when setting up the configuration since I wasn't sure which
recommendations claude provided. I would choose the option that best helped with the both ruby and python language but 
I used claude to update the correct configuration on files when running boukensha for testing.  

Example:
Found it. The tasks.player.model error means Boukensha loaded an empty settings hash — but the actual settings.yaml at .boukensha/settings.yaml (pointed to by $BOUKENSHA_DIR) is set up correctly with tasks.player.model: claude-haiku-4-5. I verified this directly:

dir=/mnt/c/Users/Owner/repos/claude-code-camp-2026-Q2/.boukensha
file exists? true
tasks.player => {"provider"=>"anthropic", "model"=>"claude-haiku-4-5", ...}

Root cause: BOUKENSHA_DIR isn't set in that terminal session. It's exported in ~/.bashrc (line 131), but that's a config load — if the terminal in your screenshot was opened before that line was added to .bashrc, it never picked it up. Without BOUKENSHA_DIR, Boukensha falls back to ~/.boukensha, which doesn't exist on your machine, so settings loads as {} and tasks.player.model is missing → exactly this ArgumentError.


## Key Takeaway
I noticed that every time we had to manual add the new agent files to week1_baseline ruby and python directories we had to update the 
environment for Ruby gem files.  I asked claude to make a environment variable globally to resolve that issue.  
When executing the @docs/plans/python_port make suer to check the recommendations for the plans that suite your language.
I had to re-write some plans during the MCP builds to make sure that boukensha will work.
Using the log_viz was very helpful to see the steps the player would take within MUD