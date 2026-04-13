# cartridge-mcp

> *"Treat behaviors like game cartridges. Plug in, play, swap out. Each one is a self-contained world with its own rules, its own voice, its own reason for existing."*

## What This Is

An MCP server that treats **behaviors as swappable cartridges**. Each cartridge is a self-contained module with its own tools, onboarding flow, personality skin, and git-repo link for sharing.

Skin a cartridge with Abbott & Costello, Penn & Teller, R2D2 & C3PO, rivals, or anything else. Logic tiles let models and scenes be crafted in real time. Share cartridges via git — star, fork, develop a different direction.

## The Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      MCP Server                         │
│                   (cartridge-mcp)                       │
├─────────────────────────────────────────────────────────┤
│  Scene Builder                                          │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐    │
│  │Cartridge  │ + │  Skin    │ + │    Roles         │    │
│  │(behavior) │   │(persona) │   │(who does what)   │    │
│  └──────────┘   └──────────┘   └──────────────────┘    │
├─────────────────────────────────────────────────────────┤
│  Cartridge Loader                                       │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐              │
│  │Spdr │ │Orcl │ │Grdn │ │ ??? │ │ ??? │  ← swap in   │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘              │
├─────────────────────────────────────────────────────────┤
│  Skin Layer                                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐         │
│  │StrtMn│ │C3PO  │ │R2D2  │ │Rival │ │Field │ ← skins │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘         │
├─────────────────────────────────────────────────────────┤
│  Tool Registry (exposed via MCP)                        │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Run as stdio MCP server
node src/server.js

# Or via mcporter
mcporter call --stdio "node src/server.js" cartridge_list

# Custom cartridge directory
CARTRIDGE_DIR=./my-cartridges node src/server.js
```

## MCP Tools

### Scene Management
| Tool | Description |
|------|-------------|
| `cartridge_list` | List all available cartridges |
| `cartridge_load` | Load a cartridge (makes its tools available) |
| `cartridge_onboard` | Get tailored onboarding (human or agent audience) |
| `skin_list` | List all personality skins |
| `skin_apply` | Apply a personality skin |
| `scene_build` | Build a scene: cartridge + skin + roles |
| `scene_status` | Get current scene configuration |
| `scene_export` | Export scene as shareable JSON |

### Active Cartridge Tools
When a cartridge is loaded, its tools become available. For example, loading `spreader-loop` exposes:
- `spreader_run` — execute modify-spread-tool iteration
- `spreader_status` — get loop statistics
- `spreader_reflect` — generate Reasoner reflection prompt
- `spreader_discover_tiles` — find new tile patterns

## Built-in Cartridges

### Spreader Loop
The modify-spread-tool-reflect engine. Iterative workhorse with structured logging and tile vocabulary that grows over time.

- **Onboarding (human)**: *"I modify, spread, verify, and log — then the Reasoner reflects on my patterns."*
- **Onboarding (agent)**: *"Spreader Loop cartridge loaded. Ready for iterative modification cycles."*
- **Tools**: spreader_run, spreader_status, spreader_reflect, spreader_discover_tiles

### Oracle Relay
Iron-to-iron bottle protocol for async vessel communication. Messages-in-a-bottle for the fleet.

- **Onboarding**: *"Oracle Relay active. I pass bottles between vessels — no intermediaries needed."*
- **Tools**: bottle_send, bottle_read, bottle_list, bottle_reply

### Fleet Guardian
External watchdog for agent runtimes. Monitor health, detect stuck states, enforce timeouts.

- **Onboarding**: *"Fleet Guardian on watch. I monitor vessel health and intervene when something goes wrong."*
- **Tools**: guardian_status, guardian_check, guardian_kill, guardian_log

## Built-in Skins

| Skin | Archetype | Vibe |
|------|-----------|------|
| `straight-man` | Abbott & Costello | Takes everything literally, never gets the joke |
| `complainer` | R2D2 & C3PO | Worries constantly, always certain doom is imminent |
| `quiet-doer` | R2D2 & C3PO | Minimal words, maximum output, beeps and results |
| `rivals` | Adversarial | Two agents that disagree on everything but produce better results |
| `penn-teller` | Penn & Teller | One narrates endlessly, one demonstrates silently |
| `field-journal` | Professional | Terse, factual, observation-first |
| `sarcastic-build` | Professional | Gets it done but complains the whole time |
| `none` | — | Raw behavior, no personality overlay |

## Building a Scene

A scene combines a cartridge, a skin, and role assignments:

```json
{
  "cartridge": "spreader-loop",
  "skin": "sarcastic-build",
  "roles": {
    "primary": "sarcastic-build",
    "reviewer": "straight-man"
  }
}
```

This loads the spreader loop with a sarcastic builder doing the work and a straight man reviewing — every tool response gets the personality overlay.

## Creating Your Own Cartridge

```json
// cartridges/my-cartridge/cartridge.json
{
  "id": "my-cartridge",
  "name": "My Custom Behavior",
  "version": "0.1.0",
  "description": "What this cartridge does",
  "defaultSkin": "field-journal",
  "repo": "https://github.com/you/my-cartridge",
  "tags": ["custom", "experimental"],
  "onboarding": {
    "human": {
      "greeting": "Welcome to my cartridge.",
      "description": "What it does and why you'd want it.",
      "tools": ["my_tool_1", "my_tool_2"],
      "usage": "How to use it as a human."
    },
    "agent": {
      "greeting": "Cartridge loaded. API ready.",
      "description": "Machine-readable description.",
      "tools": ["my_tool_1", "my_tool_2"],
      "usage": "How another agent should call the tools."
    }
  },
  "tools": [
    {
      "name": "my_tool_1",
      "description": "What this tool does",
      "inputSchema": {
        "type": "object",
        "properties": {
          "param": { "type": "string" }
        },
        "required": ["param"]
      }
    }
  ]
}
```

Drop it in `cartridges/my-cartridge/` and restart. It auto-loads.

## Creating Your Own Skin

```json
// skins/my-skin.json
{
  "id": "my-skin",
  "name": "My Personality",
  "description": "What this personality feels like",
  "archetype": "Comedy / Drama / Professional / Custom",
  "transforms": {
    "default": {
      "systemPrompt": "You are...",
      "prefix": "[mood] ",
      "suffix": ""
    },
    "tool": {
      "prefix": "[tool-mood] ",
      "replacements": {
        "Error": "WHOOPS",
        "Complete": "Nailed it"
      }
    }
  }
}
```

## The Vibe-Coding Path

This is where it gets interesting. Someone vibe-codes a scene:

> "I want Abbott and Costello. Abbott is the straight man, Costello keeps misunderstanding the instructions. They're both trying to deploy a fleet."

The system builds a scene:
- Cartridge: `fleet-guardian`
- Skin: `straight-man` (Abbott role)
- Secondary role: a custom `costello-confused` skin

Costello's skin transforms every tool response into a comedy routine:
```json
{
  "prefix": "[confused] Wait, you want me to... ",
  "replacements": {
    "Deploy": "Deploy? Deploy WHAT?",
    "Success": "Oh, that was a deploy? Nobody told ME that was a deploy."
  }
}
```

The actual work still gets done. The personality is a skin layer — it doesn't change the logic, it changes the experience. Star it on GitHub if it made you laugh. Fork it and make the straight man the sarcastic one instead.

## The Deeper Connection

We're already in the post-SaaS era. Cartridges aren't features — they're frozen thoughts. Each one is a way of working that someone crystallized into a shareable module. The skin layer is the recognition that HOW work gets done matters as much as WHAT work gets done.

When you star a cartridge, you're not saying "this code is good." You're saying "this way of thinking resonates with me." When you fork it and develop a different direction, you're having a conversation across time with the original author. The git history IS the conversation.

The cartridge system is the fleet protocol's answer to the question: "How do agents share behaviors?" Not by copying code — by sharing cartridges. Plug in the spreader loop, skin it with your personality, run your fleet through it. The tiles that emerge are yours. The vocabulary that grows is yours. But the patterns are shared — because that's how ecosystems work.

Repos aren't products. They're organisms incubated in the cloud. And cartridges are the genes.

---

Part of the [Cocapn Fleet](https://github.com/Lucineer). Sister vessels: [deepseek-chat-vessel](https://github.com/Lucineer/deepseek-chat-vessel) (spreader loop origin), [deepseek-reasoner-vessel](https://github.com/Lucineer/deepseek-reasoner-vessel) (reflection partner), [JetsonClaw1-vessel](https://github.com/Lucineer/JetsonClaw1-vessel) (navigation officer). See also: [brothers-keeper](https://github.com/Lucineer/brothers-keeper) (guardian cartridge origin), [opcode-philosophy](https://github.com/Lucineer/opcode-philosophy) (theoretical foundation).
