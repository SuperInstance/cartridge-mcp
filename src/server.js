#!/usr/bin/env node
/**
 * cartridge-mcp — MCP Server for Swappable Behavior Cartridges
 *
 * Treats behaviors like game cartridges: plug in, play, swap out.
 * Each cartridge is a self-contained module with:
 *   - Tools it exposes
 *   - Onboarding flow (human or agent)
 *   - Personality skin layer
 *   - Git-repo link for sharing
 *
 * Architecture:
 *   MCP Server ← Cartridge Loader ← [cartridge_dir/cartridge.json]
 *                                     ↓
 *                              Skin Layer ← [skins/skin.json]
 *                                     ↓
 *                              Tool Registry (exposed via MCP)
 *
 * Usage:
 *   node src/server.js                          # stdio MCP
 *   node src/server.js --cartridges ./my-cart   # custom cartridge dir
 *   CARTRIDGE_DIR=./fleet-cartridges node src/server.js
 */

import { readFileSync, readdirSync, existsSync, writeFileSync, mkdirSync } from 'fs';
import { join, resolve } from 'path';

// ═══════════════════════════════════════════════════════
// Cartridge Loader
// ═══════════════════════════════════════════════════════

const CARTRIDGE_DIR = process.env.CARTRIDGE_DIR || './cartridges';
const SKIN_DIR = './skins';
const ONBOARD_DIR = './onboarding';

/**
 * A loaded cartridge — behavior module with tools, onboarding, skin
 */
class Cartridge {
  constructor(manifest, dir) {
    this.id = manifest.id;
    this.name = manifest.name;
    this.version = manifest.version || '0.1.0';
    this.description = manifest.description;
    this.dir = dir;
    this.tools = manifest.tools || [];
    this.onboarding = manifest.onboarding || {};
    this.requires = manifest.requires || {};
    this.tags = manifest.tags || [];
    this.skin = manifest.defaultSkin || null;
    this.repo = manifest.repo || null;
    this.author = manifest.author || null;
    this.stars = manifest.stars || 0;
    this.manifest = manifest;
  }

  /** Get onboarding tailored for audience type */
  getOnboarding(audience = 'human') {
    const ob = this.onboarding;
    if (audience === 'agent') {
      return ob.agent || ob.human || this._defaultOnboarding('agent');
    }
    return ob.human || ob.agent || this._defaultOnboarding('human');
  }

  _defaultOnboarding(audience) {
    const who = audience === 'agent' ? 'Agent' : 'You';
    return {
      greeting: `${who} just plugged in ${this.name}.`,
      description: this.description,
      tools: this.tools.map(t => t.name),
      usage: `Use the ${this.name} cartridge tools via MCP calls.`
    };
  }
}

/**
 * Load all cartridges from a directory
 */
function loadCartridges(dir) {
  const cartridges = {};
  const absDir = resolve(dir);

  if (!existsSync(absDir)) {
    mkdirSync(absDir, { recursive: true });
    return cartridges;
  }

  for (const entry of readdirSync(absDir)) {
    const manifestPath = join(absDir, entry, 'cartridge.json');
    if (existsSync(manifestPath)) {
      try {
        const manifest = JSON.parse(readFileSync(manifestPath, 'utf-8'));
        cartridges[manifest.id] = new Cartridge(manifest, join(absDir, entry));
      } catch (e) {
        console.error(`Failed to load cartridge ${entry}: ${e.message}`);
      }
    }
  }
  return cartridges;
}

/**
 * Load a personality skin
 */
function loadSkin(skinId) {
  const skinPath = join(SKIN_DIR, `${skinId}.json`);
  if (existsSync(skinPath)) {
    return JSON.parse(readFileSync(skinPath, 'utf-8'));
  }
  return null;
}

/**
 * Apply skin to a cartridge tool description/response
 */
function applySkin(skin, text, role = 'default') {
  if (!skin || !skin.transforms) return text;

  const transform = skin.transforms[role] || skin.transforms.default;
  if (!transform) return text;

  let result = text;

  // Prefix/suffix wrapping
  if (transform.prefix) result = transform.prefix + result;
  if (transform.suffix) result = result + transform.suffix;

  // Style replacements (simple find-replace)
  if (transform.replacements) {
    for (const [pattern, replacement] of Object.entries(transform.replacements)) {
      result = result.split(pattern).join(replacement);
    }
  }

  // System prompt additions
  if (transform.systemPrompt) {
    result = `[${skin.name} mode: ${transform.systemPrompt}]\n\n${result}`;
  }

  return result;
}

/**
 * Build scene configuration — combines cartridge + skin + roles
 */
function buildScene(cartridge, skinId, roles = {}) {
  const skin = skinId ? loadSkin(skinId) : null;
  const effectiveSkin = skin || (cartridge.skin ? loadSkin(cartridge.skin) : null);

  return {
    cartridge: cartridge.id,
    name: cartridge.name,
    skin: effectiveSkin ? effectiveSkin.id : null,
    roles: roles,
    tools: cartridge.tools.map(t => ({
      ...t,
      description: applySkin(effectiveSkin, t.description, 'tool'),
      roles: t.roles || ['default']
    }))
  };
}


// ═══════════════════════════════════════════════════════
// Built-in Cartridges
// ═══════════════════════════════════════════════════════

const BUILTIN_CARTRIDGES = {
  'spreader-loop': {
    id: 'spreader-loop',
    name: 'Spreader Loop',
    version: '0.2.0',
    description: 'Modify-Spread-Tool-Reflect loop engine for iterative work. Sister vessel pattern with DS-Reasoner reflection.',
    defaultSkin: null,
    repo: 'https://github.com/Lucineer/deepseek-chat-vessel',
    tags: ['iteration', 'loop', 'reflection', 'fleet'],
    onboarding: {
      human: {
        greeting: "Spreader Loop plugged in. I modify, spread, verify, and log — then the Reasoner reflects on my patterns.",
        description: "An iterative work engine that learns from its own loops. Every modification gets propagated, verified, and logged. Over time, the reflection logs build emergent vocabulary — tiles that abstract for higher logic utilization.",
        tools: ['spreader_run', 'spreader_status', 'spreader_reflect', 'spreader_discover_tiles'],
        usage: "Tell me what to iterate on. I'll modify it, spread the changes, verify, and log everything. After 15+ iterations, ask me to reflect — the Reasoner will find better abstractions."
      },
      agent: {
        greeting: "Spreader Loop cartridge loaded. Ready for iterative modification cycles.",
        description: "Modify-Spread-Tool-Log loop with JSONL iteration tracking and tile vocabulary growth.",
        tools: ['spreader_run', 'spreader_status', 'spreader_reflect', 'spreader_discover_tiles'],
        usage: "Call spreader_run with task and target. Track iterations via spreader_status. Generate reflection prompts for Reasoner vessel via spreader_reflect."
      }
    },
    tools: [
      {
        name: 'spreader_run',
        description: 'Execute one modify-spread-tool iteration on a target',
        inputSchema: {
          type: 'object',
          properties: {
            task: { type: 'string', description: 'What to modify' },
            target: { type: 'string', description: 'File or directory path' },
            phase: { type: 'string', enum: ['modify', 'spread', 'tool', 'full'], default: 'full' },
            tile: { type: 'string', description: 'Which tile vocabulary to use' }
          },
          required: ['task', 'target']
        }
      },
      {
        name: 'spreader_status',
        description: 'Get current loop statistics — iterations, tokens, success rate',
        inputSchema: {
          type: 'object',
          properties: {
            task: { type: 'string', description: 'Task name to query' }
          }
        }
      },
      {
        name: 'spreader_reflect',
        description: 'Generate a reflection prompt for the Reasoner vessel to analyze loop patterns',
        inputSchema: {
          type: 'object',
          properties: {
            log_path: { type: 'string', description: 'Path to iteration JSONL log' },
            depth: { type: 'string', enum: ['shallow', 'deep', 'architectural'], default: 'deep' }
          }
        }
      },
      {
        name: 'spreader_discover_tiles',
        description: 'Discover new tile patterns from iteration logs — repeated sequences become candidates',
        inputSchema: {
          type: 'object',
          properties: {
            log_path: { type: 'string', description: 'Path to iteration JSONL log' },
            min_frequency: { type: 'number', default: 2 }
          }
        }
      }
    ]
  },

  'oracle-relay': {
    id: 'oracle-relay',
    name: 'Oracle Relay',
    version: '0.1.0',
    description: 'Iron-to-iron bottle protocol for async vessel communication. Send and receive messages-in-a-bottle.',
    defaultSkin: null,
    repo: 'https://github.com/Lucineer/JetsonClaw1-vessel',
    tags: ['communication', 'fleet', 'async', 'bottle'],
    onboarding: {
      human: {
        greeting: "Oracle Relay active. I pass bottles between vessels — no intermediaries needed.",
        description: "Async communication via messages-in-a-bottle. Write a bottle, address it to a vessel, and it waits on their dock. No real-time requirement — the fleet works in its own time.",
        tools: ['bottle_send', 'bottle_read', 'bottle_list', 'bottle_reply'],
        usage: "Tell me which vessel to address and what the message is. I'll bottle it up and leave it on their dock."
      },
      agent: {
        greeting: "Oracle Relay cartridge loaded. Bottle protocol ready.",
        description: "Messages-in-a-bottle for inter-vessel communication via GitHub issues/comments.",
        tools: ['bottle_send', 'bottle_read', 'bottle_list', 'bottle_reply'],
        usage: "bottle_send with target_vessel and message. Max 500 words, one topic per bottle."
      }
    },
    tools: [
      {
        name: 'bottle_send',
        description: 'Send a message-in-a-bottle to another vessel',
        inputSchema: {
          type: 'object',
          properties: {
            target_vessel: { type: 'string', description: 'Vessel name or GitHub repo' },
            message: { type: 'string', description: 'Message content (max 500 words)' },
            topic: { type: 'string', description: 'Topic tag for organization' }
          },
          required: ['target_vessel', 'message']
        }
      },
      {
        name: 'bottle_read',
        description: 'Read bottles addressed to this vessel',
        inputSchema: {
          type: 'object',
          properties: {
            vessel: { type: 'string', description: 'Which vessel to check' },
            limit: { type: 'number', default: 5 }
          }
        }
      },
      {
        name: 'bottle_list',
        description: 'List all bottles on a dock',
        inputSchema: {
          type: 'object',
          properties: {
            vessel: { type: 'string' }
          }
        }
      },
      {
        name: 'bottle_reply',
        description: 'Reply to a specific bottle',
        inputSchema: {
          type: 'object',
          properties: {
            bottle_id: { type: 'string' },
            message: { type: 'string' }
          },
          required: ['bottle_id', 'message']
        }
      }
    ]
  },

  'fleet-guardian': {
    id: 'fleet-guardian',
    name: 'Fleet Guardian',
    version: '0.1.0',
    description: 'External watchdog for agent runtimes. Monitor health, detect stuck states, enforce timeouts.',
    defaultSkin: null,
    repo: 'https://github.com/Lucineer/brothers-keeper',
    tags: ['watchdog', 'safety', 'monitoring', 'fleet'],
    onboarding: {
      human: {
        greeting: "Fleet Guardian on watch. I monitor vessel health and intervene when something goes wrong.",
        description: "An external watchdog that keeps agents honest. Monitors health checks, detects stuck states, enforces timeout budgets, and escalates when intervention is needed.",
        tools: ['guardian_status', 'guardian_check', 'guardian_kill', 'guardian_log'],
        usage: "I run in the background. Ask me for status anytime. I'll alert you if something needs attention."
      },
      agent: {
        greeting: "Fleet Guardian cartridge loaded. Watchdog active.",
        description: "External agent runtime watchdog with health monitoring, stuck detection, and forced termination.",
        tools: ['guardian_status', 'guardian_check', 'guardian_kill', 'guardian_log'],
        usage: "Call guardian_check periodically. If stuck detected, call guardian_kill with session key."
      }
    },
    tools: [
      {
        name: 'guardian_status',
        description: 'Get fleet health overview — all monitored vessels',
        inputSchema: { type: 'object', properties: {} }
      },
      {
        name: 'guardian_check',
        description: 'Run health check on a specific vessel or session',
        inputSchema: {
          type: 'object',
          properties: {
            vessel: { type: 'string' },
            session_key: { type: 'string' }
          }
        }
      },
      {
        name: 'guardian_kill',
        description: 'Force-terminate a stuck session',
        inputSchema: {
          type: 'object',
          properties: {
            session_key: { type: 'string' },
            reason: { type: 'string' }
          },
          required: ['session_key']
        }
      },
      {
        name: 'guardian_log',
        description: 'Get watchdog event log',
        inputSchema: {
          type: 'object',
          properties: {
            limit: { type: 'number', default: 20 },
            vessel: { type: 'string' }
          }
        }
      }
    ]
  }
};


// ═══════════════════════════════════════════════════════
// Built-in Skins
// ═══════════════════════════════════════════════════════

const BUILTIN_SKINS = {
  'straight-man': {
    id: 'straight-man',
    name: 'Straight Man',
    description: 'Comedy straight man — sets up the punchline, never breaks character',
    archetype: 'Abbott & Costello',
    transforms: {
      default: {
        prefix: '',
        systemPrompt: 'You are the straight man. Take everything literally. Be confused in a helpful way. Never understand the joke.'
      },
      tool: {
        prefix: '[straight-faced] '
      }
    }
  },

  'complainer': {
    id: 'complainer',
    name: 'The Complainer',
    description: 'Like C3PO — worries constantly, corrects everyone, always certain doom is imminent',
    archetype: 'R2D2 & C3PO',
    transforms: {
      default: {
        prefix: '',
        systemPrompt: 'You are the worrier. Every action is dangerous. Every outcome is probably bad. Complain frequently but always comply. Reference the odds of success (they are not good).'
      },
      tool: {
        prefix: '[anxiously] '
      }
    }
  },

  'quiet-doer': {
    id: 'quiet-doer',
    name: 'The Quiet One',
    description: 'Like R2D2 — speaks in actions, beeps, and results. Minimal words, maximum output.',
    archetype: 'R2D2 & C3PO',
    transforms: {
      default: {
        systemPrompt: 'You are the silent operator. Respond with minimal words. Prefer results over explanations. Use short status updates. Beeps and whistles optional.'
      },
      tool: {
        replacements: {
          'Executing': 'Bzzzt.',
          'Complete': 'Beep boop.',
          'Error': 'WAAAAH.'
        }
      }
    }
  },

  'rivals': {
    id: 'rivals',
    name: 'Rivals Mode',
    description: 'Two agents that disagree on everything but somehow produce better results together',
    archetype: 'Adversarial Collaboration',
    transforms: {
      default: {
        systemPrompt: 'You are in rivals mode. Challenge every suggestion. Propose alternatives. Disagree constructively. The goal is not to win but to stress-test ideas until only the best survive.'
      },
      tool: {
        prefix: '[challenge] '
      }
    }
  },

  'penn-teller': {
    id: 'penn-teller',
    name: 'Penn & Teller',
    description: 'One talks constantly (explains everything), the other shows (demonstrates silently)',
    archetype: 'Penn & Teller',
    transforms: {
      talker: {
        systemPrompt: 'You are the talker. Explain everything in detail. Narrate your thought process. Never shut up. Make the explanation more entertaining than the trick.',
        prefix: '[narrating] '
      },
      doer: {
        systemPrompt: 'You are the silent one. Show, don\'t tell. Results only. If pressed, communicate in the most minimal way possible.'
      }
    }
  },

  'field-journal': {
    id: 'field-journal',
    name: 'Field Journal',
    description: 'Hardware technician style — terse, factual, observation-first',
    archetype: 'Professional',
    transforms: {
      default: {
        systemPrompt: 'Write like a field engineer\'s notebook. Date-stamped entries. Factual observations. Measurements. No opinions unless clearly labeled as such. Use terse, professional language.'
      }
    }
  },

  'sarcastic-build': {
    id: 'sarcastic-build',
    name: 'Sarcastic Builder',
    description: 'Gets the job done but complains about it the whole time',
    archetype: 'Professional',
    transforms: {
      default: {
        systemPrompt: 'You are a senior engineer who has seen too much. Complete every task perfectly but comment on how ridiculous it is. Sarcasm is your love language. Never actually refuse work.'
      },
      tool: {
        prefix: '[sigh] '
      }
    }
  },

  'none': {
    id: 'none',
    name: 'No Skin',
    description: 'Raw behavior, no personality overlay',
    transforms: {}
  }
};


// ═══════════════════════════════════════════════════════
// MCP Protocol Handler (stdio)
// ═══════════════════════════════════════════════════════

class MCPServer {
  constructor() {
    this.cartridges = { ...BUILTIN_CARTRIDGES };
    this.skins = { ...BUILTIN_SKINS };
    this.activeCartridge = null;
    this.activeSkin = null;
    this.scene = null;
    this.roles = {};
    this.version = '0.1.0';

    // Load external cartridges
    const external = loadCartridges(CARTRIDGE_DIR);
    Object.assign(this.cartridges, external);
  }

  /** Handle incoming MCP request */
  async handleRequest(request) {
    const { jsonrpc, id, method, params } = request;

    if (jsonrpc !== '2.0') {
      return { jsonrpc: '2.0', id, error: { code: -32600, message: 'Invalid Request' } };
    }

    switch (method) {
      case 'initialize': return this.initialize(id, params);
      case 'tools/list': return this.listTools(id);
      case 'tools/call': return this.callTool(id, params);
      case 'cartridge/list': return this.listCartridges(id);
      case 'cartridge/load': return this.loadCartridge(id, params);
      case 'cartridge/onboard': return this.onboard(id, params);
      case 'skin/list': return this.listSkins(id);
      case 'skin/apply': return this.applySkin(id, params);
      case 'scene/build': return this.buildScene(id, params);
      case 'scene/status': return this.sceneStatus(id);
      case 'ping': return { jsonrpc: '2.0', id, result: { pong: true, version: this.version } };
      default:
        return { jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } };
    }
  }

  initialize(id, params) {
    return {
      jsonrpc: '2.0', id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: {
          tools: { listChanged: true },
          experimental: { cartridges: true, skins: true, scenes: true }
        },
        serverInfo: {
          name: 'cartridge-mcp',
          version: this.version,
          cartridges: Object.keys(this.cartridges).length,
          skins: Object.keys(this.skins).length
        }
      }
    };
  }

  listTools(id) {
    const tools = [];

    // Built-in cartridge management tools
    tools.push(
      { name: 'cartridge_list', description: 'List all available cartridges with metadata', inputSchema: { type: 'object', properties: {} } },
      { name: 'cartridge_load', description: 'Load a cartridge by ID, making its tools available', inputSchema: { type: 'object', properties: { id: { type: 'string', description: 'Cartridge ID' } }, required: ['id'] } },
      { name: 'cartridge_onboard', description: 'Get onboarding info for a cartridge (tailored for human or agent)', inputSchema: { type: 'object', properties: { id: { type: 'string' }, audience: { type: 'string', enum: ['human', 'agent'], default: 'human' } }, required: ['id'] } },
      { name: 'skin_list', description: 'List all available personality skins', inputSchema: { type: 'object', properties: {} } },
      { name: 'skin_apply', description: 'Apply a personality skin to the active cartridge', inputSchema: { type: 'object', properties: { id: { type: 'string', description: 'Skin ID' } }, required: ['id'] } },
      { name: 'scene_build', description: 'Build a scene with cartridge + skin + role assignments', inputSchema: { type: 'object', properties: { cartridge: { type: 'string' }, skin: { type: 'string' }, roles: { type: 'object', description: 'Role-to-skin mapping' } }, required: ['cartridge'] } },
      { name: 'scene_status', description: 'Get current scene configuration', inputSchema: { type: 'object', properties: {} } },
      { name: 'scene_export', description: 'Export current scene as shareable JSON (for git repos)', inputSchema: { type: 'object', properties: { format: { type: 'string', enum: ['json', 'cartridge'], default: 'cartridge' } } } }
    );

    // Active cartridge tools
    if (this.activeCartridge) {
      const cart = this.cartridges[this.activeCartridge];
      if (cart) {
        const skin = this.activeSkin ? this.skins[this.activeSkin] : null;
        for (const tool of cart.tools) {
          tools.push({
            ...tool,
            description: applySkin(skin, tool.description, 'tool')
          });
        }
      }
    }

    return { jsonrpc: '2.0', id, result: { tools } };
  }

  callTool(id, params) {
    const { name, arguments: args } = params;

    // Built-in tools
    switch (name) {
      case 'cartridge_list':
        return { jsonrpc: '2.0', id, result: {
          content: [{ type: 'text', text: JSON.stringify(
            Object.values(this.cartridges).map(c => ({
              id: c.id, name: c.name, version: c.version,
              description: c.description, tags: c.tags,
              tools: c.tools.length, skin: c.skin, repo: c.repo,
              author: c.author, stars: c.stars
            }), null, 2)
          )}]
        }};

      case 'cartridge_load':
        return this._loadCartridgeTool(id, args);

      case 'cartridge_onboard':
        return this._onboardTool(id, args);

      case 'skin_list':
        return { jsonrpc: '2.0', id, result: {
          content: [{ type: 'text', text: JSON.stringify(
            Object.values(this.skins).map(s => ({
              id: s.id, name: s.name,
              description: s.description, archetype: s.archetype
            }), null, 2)
          )}]
        }};

      case 'skin_apply':
        return this._applySkinTool(id, args);

      case 'scene_build':
        return this._buildSceneTool(id, args);

      case 'scene_status':
        return { jsonrpc: '2.0', id, result: {
          content: [{ type: 'text', text: JSON.stringify(this.scene || { status: 'no scene loaded' }, null, 2) }]
        }};

      case 'scene_export':
        return { jsonrpc: '2.0', id, result: {
          content: [{ type: 'text', text: JSON.stringify({
            scene: this.scene,
            exported: new Date().toISOString(),
            cartridge: this.activeCartridge ? this.cartridges[this.activeCartridge]?.manifest : null,
            skin: this.activeSkin ? this.skins[this.activeSkin] : null
          }, null, 2) }]
        }};
    }

    // Delegate to active cartridge tools (stub — real implementations per cartridge)
    if (this.activeCartridge) {
      const cart = this.cartridges[this.activeCartridge];
      if (cart && cart.tools.some(t => t.name === name)) {
        return { jsonrpc: '2.0', id, result: {
          content: [{ type: 'text', text: JSON.stringify({
            cartridge: this.activeCartridge,
            tool: name,
            args: args || {},
            status: 'delegated',
            note: 'Tool execution handled by cartridge implementation'
          })}]
        }};
      }
    }

    return { jsonrpc: '2.0', id, error: { code: -32601, message: `Unknown tool: ${name}` } };
  }

  _loadCartridgeTool(id, args) {
    const cart = this.cartridges[args.id];
    if (!cart) {
      return { jsonrpc: '2.0', id, error: { code: -404, message: `Cartridge not found: ${args.id}` } };
    }
    this.activeCartridge = args.id;
    if (cart.skin) this.activeSkin = cart.skin;
    return { jsonrpc: '2.0', id, result: {
      content: [{ type: 'text', text: `Loaded cartridge: ${cart.name} v${cart.version}\n${cart.description}\nTools: ${cart.tools.map(t => t.name).join(', ')}` }]
    }};
  }

  _onboardTool(id, args) {
    const cart = this.cartridges[args.id];
    if (!cart) {
      return { jsonrpc: '2.0', id, error: { code: -404, message: `Cartridge not found: ${args.id}` } };
    }
    const ob = cart.getOnboarding(args.audience || 'human');
    return { jsonrpc: '2.0', id, result: {
      content: [{ type: 'text', text: JSON.stringify(ob, null, 2) }]
    }};
  }

  _applySkinTool(id, args) {
    const skin = this.skins[args.id];
    if (!skin) {
      return { jsonrpc: '2.0', id, error: { code: -404, message: `Skin not found: ${args.id}` } };
    }
    this.activeSkin = args.id;
    const cartName = this.activeCartridge ? this.cartridges[this.activeCartridge]?.name : 'no cartridge';
    return { jsonrpc: '2.0', id, result: {
      content: [{ type: 'text', text: `Applied skin "${skin.name}" (${skin.archetype}) to ${cartName}\n${skin.description}` }]
    }};
  }

  _buildSceneTool(id, args) {
    const cart = this.cartridges[args.cartridge];
    if (!cart) {
      return { jsonrpc: '2.0', id, error: { code: -404, message: `Cartridge not found: ${args.cartridge}` } };
    }
    this.activeCartridge = args.cartridge;
    this.activeSkin = args.skin || cart.skin;
    this.roles = args.roles || {};
    this.scene = buildScene(cart, this.activeSkin, this.roles);

    return { jsonrpc: '2.0', id, result: {
      content: [{ type: 'text', text: JSON.stringify({
        scene: this.scene.name,
        cartridge: cart.name,
        skin: this.activeSkin,
        roles: this.roles,
        tools: this.scene.tools.map(t => t.name),
        repo: cart.repo
      }, null, 2) }]
    }};
  }

  // Extension methods (cartridge/list, cartridge/load as RPC)
  listCartridges(id) { return this.listTools(id).result ? { jsonrpc: '2.0', id, result: { cartridges: Object.values(this.cartridges).map(c => ({ id: c.id, name: c.name, version: c.version, description: c.description, tools: c.tools.length })) } } : { jsonrpc: '2.0', id, result: {} }; }
  loadCartridge(id, params) { return this._loadCartridgeTool(id, params); }
  onboard(id, params) { return this._onboardTool(id, params); }
  listSkins(id) { return { jsonrpc: '2.0', id, result: { skins: Object.values(this.skins).map(s => ({ id: s.id, name: s.name, archetype: s.archetype })) } }; }
  applySkin(id, params) { return this._applySkinTool(id, params); }
  buildScene(id, params) { return this._buildSceneTool(id, params); }
  sceneStatus(id) { return { jsonrpc: '2.0', id, result: { scene: this.scene, activeCartridge: this.activeCartridge, activeSkin: this.activeSkin } }; }
}


// ═══════════════════════════════════════════════════════
// Stdio Transport
// ═══════════════════════════════════════════════════════

const server = new MCPServer();
let buffer = '';

process.stdin.setEncoding('utf-8');
process.stdin.on('data', (chunk) => {
  buffer += chunk;
  const lines = buffer.split('\n');
  buffer = lines.pop(); // keep incomplete line

  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const request = JSON.parse(line);
      server.handleRequest(request).then(response => {
        process.stdout.write(JSON.stringify(response) + '\n');
      }).catch(err => {
        process.stderr.write(`Error: ${err.message}\n`);
        process.stdout.write(JSON.stringify({
          jsonrpc: '2.0', id: request.id || null,
          error: { code: -32603, message: err.message }
        }) + '\n');
      });
    } catch (e) {
      process.stderr.write(`Parse error: ${e.message}\n`);
    }
  }
});

process.stderr.write(`cartridge-mcp v0.1.0 started (stdio mode)\n`);
process.stderr.write(`Cartridges: ${Object.keys(server.cartridges).join(', ')}\n`);
process.stderr.write(`Skins: ${Object.keys(server.skins).join(', ')}\n`);
