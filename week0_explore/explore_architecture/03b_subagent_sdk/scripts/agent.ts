#!/usr/bin/env -S npx tsx
// SDK-driven counterpart to 03a's filesystem `.claude/agents/mud-play.md`:
// the mud-player agent is defined here in code via `AgentDefinition` and
// handed to `query()` directly, instead of being auto-discovered from a
// `.claude/agents/` directory by the Claude Code harness.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { createInterface } from "node:readline/promises";
import { fileURLToPath } from "node:url";

import matter from "gray-matter";
import {
  query,
  type AgentDefinition,
  type SDKAssistantMessage,
  type SDKUserMessage,
} from "@anthropic-ai/claude-agent-sdk";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = join(__dirname, "..");

function loadAgentDefinition(markdownPath: string): AgentDefinition {
  const { data, content } = matter(readFileSync(markdownPath, "utf8"));

  const tools =
    typeof data.tools === "string"
      ? data.tools
          .split(",")
          .map((tool: string) => tool.trim())
          .filter(Boolean)
      : undefined;

  return {
    description: data.description,
    prompt: content.trim(),
    ...(tools ? { tools } : {}),
    ...(data.model ? { model: data.model } : {}),
  };
}

const mudPlayer = loadAgentDefinition(join(PROJECT_ROOT, "agents", "mud-player.md"));

async function* userMessages(
  rl: ReturnType<typeof createInterface>,
): AsyncGenerator<SDKUserMessage> {
  for await (const line of rl) {
    const text = line.trim();
    if (!text) {
      rl.prompt();
      continue;
    }
    if (text === "/exit" || text === "/quit") {
      return;
    }
    yield {
      type: "user",
      message: { role: "user", content: text },
      parent_tool_use_id: null,
    };
  }
}

function printAssistantMessage(message: SDKAssistantMessage): void {
  for (const block of message.message.content) {
    if (block.type === "text") {
      process.stdout.write(block.text);
    } else if (block.type === "tool_use") {
      process.stdout.write(`\n[tool: ${block.name}] ${JSON.stringify(block.input)}\n`);
    }
  }
}

async function main(): Promise<void> {
  const rl = createInterface({
    input: process.stdin,
    output: process.stdout,
    prompt: "> ",
  });

  console.log(
    'mud-player SDK agent ready (agents/mud-player.md loaded as an AgentDefinition).\n' +
      'Type a request, e.g. "log in and look around". /exit or Ctrl-D to quit.\n',
  );
  rl.prompt();

  const stream = query({
    prompt: userMessages(rl),
    options: {
      cwd: PROJECT_ROOT,
      agents: { "mud-player": mudPlayer },
      // No interactive permission UI is wired up for this standalone driver,
      // so tool calls (the mud-player's Bash calls into scripts/mud_*.sh)
      // run without a per-call prompt. Wire up `canUseTool` instead if you
      // want to gate them.
      permissionMode: "bypassPermissions",
      systemPrompt:
        "You have a mud-player subagent available. Delegate any request " +
        "about the tbaMUD (playing, exploring, checking stats, etc.) to it " +
        "via the Task tool rather than handling it yourself.",
    },
  });

  for await (const message of stream) {
    if (message.type === "assistant") {
      printAssistantMessage(message);
    } else if (message.type === "result") {
      process.stdout.write("\n\n");
      rl.prompt();
    }
  }

  rl.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
