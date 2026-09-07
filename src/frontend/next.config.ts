import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Cloud Run: emits .next/standalone with its own server.js and only the
  // traced node_modules, so the served image needs no toolchain and no
  // `next start`. src/frontend/Dockerfile's runner stage depends on this.
  output: 'standalone',

  // `next dev` otherwise writes its own src/frontend/AGENTS.md and CLAUDE.md on
  // every boot. A nested CLAUDE.md would shadow the repo's working agreements
  // (the dry-run fence among them) for anyone working inside this package.
  agentRules: false,
};

export default nextConfig;
