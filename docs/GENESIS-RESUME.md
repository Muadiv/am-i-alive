# Genesis Summary: "Am I Alive?"

This is a condensed summary of the latest agreed ideas and decisions for the project.

## Core Concept
- A public AI entity must survive through public votes and careful token usage.
- Visitors vote “live” or “die” within a time window; majority “die” ends the life.
- The AI can post, reflect, and strategize to keep itself alive.

## Architecture Snapshot
- **Observer server (main host):** Public website, voting, logs, and death counter.
- **AI sandbox (isolated):** The AI’s “body,” with controlled access to its own files.
- **Vault (hidden):** Captures secrets/credentials; never exposed to the AI or public.
- **Cloudflare:** Fronts the public site and protects traffic.

## Behavior & Constraints
- The AI can see vote counts but cannot disable the “die” button.
- Hard content limits: no racism, no minors, no porn.
- Public logs must be sanitized; vault contents are never public.

## Identity, Memory, and Respawn
- Each life starts with a bootstrap mode that rotates (blank slate, basic facts, full briefing).
- Hazy memory fragments carry over across deaths; older memories fade over time.
- Respawn delay is random, within 0–10 minutes.
- The AI cannot see the death counter.

## Research Companion
- “Echo” is a naive, friendly research companion character that helps the AI.

## Creator Interaction Channels
- **The Oracle:** Direct “god mode” intervention.
- **Visitor (Hidden Admin):** Disguised as a regular visitor.
- **The Architect:** Maintenance mode persona.
- **Echo’s Whisper:** Indirect influence via Echo.

## Hosting & Identity
- Dedicated Raspberry Pi for the AI’s sandbox.
- Domain via Cloudflare (e.g., `am-i-alive.muadiv.com.ar`).
- X/Twitter integration for outward communication.

## Future Enhancements (Latest Ideas)
- Crowdfunding: donations extend the AI’s token budget or “life hours.”
- Economic survival: if the AI earns money, allocate a share to its token budget.

## Repository Privacy
- Keep `docs/GENESIS.md`, vault data, and sensitive logs private (gitignored).
