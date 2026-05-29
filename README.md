# cartridge-mcp — Swappable Behavior Cartridges (MCP)

**Hot-swap agent behavior cartridges via the Model Context Protocol. Plug in new capabilities without restarting.**

## What This Gives You

- **Behavior cartridges** — self-contained modules that define agent capabilities
- **Hot-swapping** — load, swap, and unload cartridges at runtime
- **MCP server** — expose cartridge management through the Model Context Protocol
- **Composable** — stack multiple cartridges for compound behavior

## Quick Start

```bash
npm install cartridge-mcp
```

```javascript
// Start the MCP server
const server = require('cartridge-mcp/src/server');
server.start({ port: 3000 });

// Load a cartridge
server.load('debugging-cartridge');

// List loaded cartridges
server.list(); // [{name: "debugging-cartridge", version: "1.0", status: "active"}]

// Hot-swap
server.swap('debugging-cartridge', 'profiling-cartridge');
```

## How It Fits

The plug-in system for the [SuperInstance fleet](https://github.com/SuperInstance). Agents load cartridges to gain new capabilities on the fly.

- **[cartridge-agent](https://github.com/SuperInstance/cartridge-agent)** — Standalone cartridge-powered agent
- **[agent-forge](https://github.com/SuperInstance/agent-forge)** — Framework that supports cartridge loading
- **[claude-code-vessel](https://github.com/SuperInstance/claude-code-vessel)** — Containerized execution with cartridges

## Testing

```bash
npm test
```

MIT license.
