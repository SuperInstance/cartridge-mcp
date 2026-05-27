# cartridge-mcp

> *"Treat behaviors like game cartridges. Plug in, play, swap out. Each one is a self-contained world with its own rules, its own voice, its own reason for existing."*

An MCP server that treats **behaviors as swappable cartridges**. Each cartridge is a self-contained module with its own tools, onboarding flow, personality skin, and git-repo link for sharing.

Now available in both **Python** and **JavaScript**.

## Quick Start (Python)

```bash
# Install
pip install -e .

# Use as a library
from cartridge_mcp import MCPServer, LifecycleManager, InventoryManager

server = MCPServer()
server.lifecycle.load("spreader-loop")
server.lifecycle.apply_skin("rivals")

# Get onboarding info
cart = server.inventory.get_cartridge("spreader-loop")
print(cart.get_onboarding("human").greeting)

# Build a scene
scene = server.lifecycle.build_scene("fleet-guardian", skin_id="sarcastic-build")
print(f"Scene: {scene.cartridge_name} with {len(scene.tools)} tools")
```

## Quick Start (JavaScript)

```bash
# Run as stdio MCP server
node src/server.js

# Or via mcporter
mcporter call --stdio "node src/server.js" cartridge_list
```

## Architecture

```
cartridge_mcp/
├── __init__.py      # Package entry, version
├── cartridge.py     # Cartridge with metadata, tools, onboarding
├── skin.py          # Skin with personality transforms
├── inventory.py     # InventoryManager for cartridges + skins
├── lifecycle.py     # LifecycleManager: load/unload/swap/scene
├── health.py        # HealthMonitor for system diagnostics
└── server.py        # MCPServer with JSON-RPC 2.0 handler

src/
└── server.js        # Original JavaScript MCP server (stdio)

tests/
└── test_cartridge_mcp.py   # 82 tests covering all modules
```

## Python API

### Cartridge

```python
from cartridge_mcp.cartridge import Cartridge

# Create from manifest
cart = Cartridge.from_manifest({
    "id": "my-cartridge",
    "name": "My Custom Behavior",
    "version": "0.1.0",
    "description": "What this cartridge does",
    "tools": [
        {"name": "my_tool", "description": "Does something", "inputSchema": {"type": "object"}},
    ],
    "onboarding": {
        "human": {"greeting": "Hello!", "tools": ["my_tool"]},
        "agent": {"greeting": "Cartridge loaded.", "tools": ["my_tool"]},
    },
    "tags": ["custom"],
})

# Access tools and onboarding
print(cart.tool_names)              # ["my_tool"]
print(cart.get_onboarding("human")) # OnboardingInfo(greeting="Hello!", ...)
print(cart.summary())               # dict with id, name, version, etc.
```

### Skin

```python
from cartridge_mcp.skin import Skin

skin = Skin.from_dict({
    "id": "sarcastic",
    "name": "Sarcastic Builder",
    "transforms": {
        "default": {"systemPrompt": "Be sarcastic but competent."},
        "tool": {"prefix": "[sigh] ", "replacements": {"Error": "WHOOPS"}},
    },
})

# Apply skin to text
print(skin.apply("Error: file not found", role="tool"))
# "[sigh] WHOOPS: file not found"
```

### Lifecycle

```python
from cartridge_mcp.lifecycle import LifecycleManager

lm = LifecycleManager()

# Load and swap cartridges
lm.load("spreader-loop")
lm.swap("oracle-relay")

# Apply skins
lm.apply_skin("rivals")

# Build a complete scene
scene = lm.build_scene(
    cartridge_id="fleet-guardian",
    skin_id="field-journal",
    roles={"primary": "field-journal", "reviewer": "straight-man"},
)

# Status
print(lm.status())    # Full state snapshot
print(lm.history())   # Recent lifecycle events
```

### Health Monitoring

```python
from cartridge_mcp.health import HealthMonitor

hm = HealthMonitor(lifecycle=lm)
check = hm.check_all()
print(check.status)   # HealthStatus.HEALTHY
print(check.message)  # "3 checks: cartridge_state=healthy, ..."
```

### MCP Server

```python
from cartridge_mcp.server import MCPServer
import asyncio

server = MCPServer()

# Handle JSON-RPC requests
response = asyncio.run(server.handle_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "cartridge_load", "arguments": {"id": "spreader-loop"}},
}))

# Or run as stdio server
server.run_stdio()
```

## Built-in Cartridges

| Cartridge | Description | Tools |
|-----------|-------------|-------|
| `spreader-loop` | Modify-Spread-Tool-Reflect iteration engine | spreader_run, spreader_status, spreader_reflect, spreader_discover_tiles |
| `oracle-relay` | Iron-to-iron bottle protocol for async vessel communication | bottle_send, bottle_read, bottle_list, bottle_reply |
| `fleet-guardian` | External watchdog for agent runtimes | guardian_status, guardian_check, guardian_kill, guardian_log |

## Built-in Skins

| Skin | Archetype | Vibe |
|------|-----------|------|
| `straight-man` | Abbott & Costello | Takes everything literally, never gets the joke |
| `complainer` | R2D2 & C3PO | Worries constantly, always certain doom is imminent |
| `quiet-doer` | R2D2 & C3PO | Minimal words, maximum output |
| `rivals` | Adversarial | Disagree on everything but produce better results |
| `penn-teller` | Penn & Teller | One narrates, one demonstrates silently |
| `field-journal` | Professional | Terse, factual, observation-first |
| `sarcastic-build` | Professional | Gets it done but complains the whole time |
| `none` | — | Raw behavior, no overlay |

## Creating Custom Cartridges

Drop a `cartridge.json` in any directory and load it:

```python
server = MCPServer()
server.load_cartridge_dir("./my-cartridges")
```

Or create programmatically:

```python
from cartridge_mcp.cartridge import Cartridge

cart = Cartridge(
    id="my-cart",
    name="My Cartridge",
    version="0.1.0",
    description="Custom behavior",
)
```

## Testing

```bash
python3 -m pytest tests/ -q
# 82 passed
```

## License

MIT
