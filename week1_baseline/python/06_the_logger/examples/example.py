import os
from pathlib import Path

from boukensha import (
    Agent,
    Anthropic,
    Client,
    Config,
    Context,
    Gemini,
    Logger,
    Ollama,
    OllamaCloud,
    OpenAI,
    Player,
    PromptBuilder,
    Registry,
)

repo_root = Path(__file__).resolve().parents[4]
os.environ.setdefault("BOUKENSHA_DIR", str(repo_root / ".boukensha"))

config = Config()
player_settings = config.tasks("player")
system_prompt = Player.system_prompt(
    player_settings,
    user_prompts_dir=config.user_prompts_dir,
    default_prompts_dir=Config.PROMPTS_DIR,
)
base_dir = Path(__file__).resolve().parent.parent

ctx = Context(task=Player, system=system_prompt)
registry = Registry(ctx)

provider = Player.provider(player_settings)
model = Player.model(player_settings)

match provider:
    case "anthropic":
        backend = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], model=model)
    case "openai":
        backend = OpenAI(api_key=os.environ["OPENAI_API_KEY"], model=model)
    case "gemini":
        backend = Gemini(api_key=os.environ["GEMINI_API_KEY"], model=model)
    case "ollama":
        backend = Ollama(model=model)
    case "ollama_cloud":
        backend = OllamaCloud(api_key=os.environ["OLLAMA_API_KEY"], model=model)
    case _:
        raise ValueError(f"Unsupported provider for player task: {provider}")

builder = PromptBuilder(ctx, backend)
client = Client(builder)
# Writes structured JSONL events to .boukensha/sessions/<session-id>.jsonl.
# Call boukensha.debug() before agent.run() to include the full raw API response in those lines.
logger = Logger()
agent = Agent(
    context=ctx,
    registry=registry,
    builder=builder,
    client=client,
    logger=logger,
    task_settings=player_settings,
)

registry.tool(
    "read_file",
    description="Read the contents of a file from disk",
    parameters={"path": {"type": "string", "description": "The file path to read"}},
    block=lambda *, path: Path(base_dir, path).resolve().read_text(),
)

registry.tool(
    "list_directory",
    description="List the files in a directory",
    parameters={"path": {"type": "string", "description": "The directory path to list"}},
    block=lambda *, path: ", ".join(f for f in os.listdir(Path(base_dir, path).resolve()) if not f.startswith(".")),
)

ctx.add_message("user", "Read the README.md file and summarise what this MUD player assistant framework can do.")

print("=== BOUKENSHA Step 6: The Logger ===")
print()
print(f"Config: {config}")
print(f"Provider: {provider}")
print(f"Model: {model}")
print(f"Max iterations: {Player.max_iterations(player_settings)}")
print(f"Max output tokens: {Player.max_output_tokens(player_settings)}")
print()

result = agent.run()

print()
print("=== FINAL RESPONSE ===")
print(result)
