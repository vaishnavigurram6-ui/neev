import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // `next dev` otherwise writes its own src/frontend/AGENTS.md and CLAUDE.md on
  // every boot. A nested CLAUDE.md would shadow the repo's working agreements
  // (the dry-run fence among them) for anyone working inside this package.
  agentRules: false,
};

export default nextConfig;
