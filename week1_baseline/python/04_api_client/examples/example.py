import json
import os
from pathlib import Path

from boukensha import (
    Anthropic,
    Client,
    Config,
    Context,
    Gemini,
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

ctx = Context(task=Player, system=system_prompt)
registry = Registry(ctx)

registry.tool(
    "read_file",
    description="Read the contents of a file from disk",
    parameters={"path": {"type": "string", "description": "The file path to read"}},
    block=lambda *, path: Path(path).read_text(),
)

registry.tool(
    "list_directory",
    description="List files in a directory",
    parameters={"path": {"type": "string", "description": "The directory path to list"}},
    block=lambda *, path: "\n".join(f for f in os.listdir(path) if not f.startswith(".")),
)

ctx.add_message("user", "What files are in the current directory?")

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

print("=== BOUKENSHA Step 4: API Client ===")
print()
print(f"Config: {config}")
print(f"Provider: {provider}")
print(f"Model: {model}")
print(f"Sending request to {builder.url}...")
print()

response = client.call()
print("Raw response:")
print(json.dumps(response, indent=2))
