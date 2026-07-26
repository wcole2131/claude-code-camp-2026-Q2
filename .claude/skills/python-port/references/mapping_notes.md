# Standing Ruby → Python mappings

These are settled across steps 00-03 of the port. Reuse them as-is in a new step's plan; only add
new mapping rows for idioms a step introduces for the first time.

| Ruby | Python equivalent | Why |
|---|---|---|
| `Dir.home` / `File.join(Dir.home, ".boukensha")` | `Path.home() / ".boukensha"` | `pathlib` is idiomatic Python; keep `Config.dir` as a `Path`, not a `str` |
| `ENV.fetch("X", nil)` | `os.environ.get("X")` | |
| `Pathname.new(raw).expand_path.to_s` | `Path(raw).expanduser().resolve()` | keep as `Path` in the Python port; callers `str()` it only for display |
| `Dotenv.load(f) if File.exist?(f)` | `if f.exists(): load_dotenv(f)` (`python-dotenv`) | |
| `YAML.safe_load(File.read(f)) \|\| {}` | `yaml.safe_load(f.read_text()) or {}` (`pyyaml`) | stdlib has no YAML support |
| `node.dig(*keys)` trying both `node[key.to_s]` and `node[key.to_sym]` | plain `dict.get(key)` | PyYAML dicts only ever have `str` keys — the symbol/string duality Ruby needs doesn't exist in Python. **Do not** invent a dual-lookup helper; it would be solving a problem Python doesn't have. |
| `hash.transform_keys(&:to_sym)` before a keyword-arg call | nothing — call `**hash` directly | Python's `**kwargs` accepts plain `str` keys; there's no symbol type to transform into |
| `Struct.new(:a, :b) { def to_s; ...; end }` | `@dataclass class X:` with a hand-written `__str__` | README explicitly frames Ruby `Struct` as "lightweight, would be a Class in practice" — `dataclass` is the direct analog, not a bespoke class |
| `attr_reader :dir, :settings` | `@property` on a plain class (or dataclass fields) | |
| `content.to_s[0..60]` (Ruby inclusive range, 61 chars) | `content[:61]` | off-by-one risk — do **not** translate `0..60` as `[:60]` |
| Class-level `NotImplementedError` (e.g. `Tasks::Base.task_name`) | duck-typed `classmethod` that raises `NotImplementedError`, not `abc.ABC`/`@abstractmethod` | these are class-level, no-instance methods; `ABC`'s instance-based abstractness doesn't map cleanly |
| `raise SomeError, "message"` / `rescue SomeError => e; e.message` | `raise SomeError("message")` / `except SomeError as e: str(e)` | plain `Exception` subclass, no custom `__init__` needed |
| method default `def f(x = {})` | `def f(x: dict \| None = None): x = x or {}` | Ruby re-evaluates default literals per call (safe); Python's mutable default is shared across calls (a bug) — never port `def f(x={})` literally |
| `puts obj` (implicit `to_s`) | `print(obj)` (implicit `__str__`) | |
| symbol args (`ctx.add_message(:user, "...")`) | plain strings (`ctx.add_message("user", "...")`) | no symbol type in Python; strings are the direct and only sensible target |
