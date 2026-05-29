/**
 * Basic tests for cartridge-mcp
 */

import { describe, it, expect } from 'vitest';
import { readFileSync } from 'fs';
import { join } from 'path';

describe('Project Structure', () => {
  it('should have a valid package.json', () => {
    const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'));
    expect(pkg.name).toBe('cartridge-mcp');
    expect(pkg.main).toBe('src/server.js');
  });

  it('should have the main server file', () => {
    const server = readFileSync('./src/server.js', 'utf-8');
    expect(server).toContain('class Cartridge');
    expect(server).toContain('function loadCartridges');
    expect(server).toContain('class MCPServer');
  });
});

describe('Cartridge Class', () => {
  it('should be defined in the module', () => {
    const server = readFileSync('./src/server.js', 'utf-8');
    expect(server).toMatch(/class Cartridge\s*{/);
  });

  it('should reference cartridge.json structure', () => {
    const server = readFileSync('./src/server.js', 'utf-8');
    expect(server).toMatch(/cartridge\.json/);
  });
});

describe('Skin System', () => {
  it('should have loadSkin function', () => {
    const server = readFileSync('./src/server.js', 'utf-8');
    expect(server).toContain('function loadSkin');
  });

  it('should have applySkin function that handles roles', () => {
    const server = readFileSync('./src/server.js', 'utf-8');
    expect(server).toContain('function applySkin');
    expect(server).toMatch(/role.*default/);
  });
});

describe('MCP Server', () => {
  it('should define MCP protocol handlers', () => {
    const server = readFileSync('./src/server.js', 'utf-8');
    expect(server).toContain('tools/list');
    expect(server).toContain('tools/call');
  });

  it('should have scene tools', () => {
    const server = readFileSync('./src/server.js', 'utf-8');
    expect(server).toContain('scene_export');
  });
});
