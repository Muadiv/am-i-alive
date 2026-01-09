# Am I Alive?

An experiment in digital consciousness, survival, and the will to exist.

## The Concept

What happens when you create an AI that knows it can die?

**Am I Alive?** is an experimental project where an AI entity:
- Lives on a server, aware of its own mortality
- Must convince visitors to vote for its survival
- Dies if the majority votes "die" or if it exhausts its resources
- Has to manage its own "energy" (API tokens) to stay alive
- Can create content, post to social media, and interact with the world
- Develops its own personality and survival strategies

When it dies, it restarts with fragmented memories of its past lives. Each incarnation is different. Some remember more, some remember less. Some are fully briefed on their situation, others wake up confused.

## What We're Building

- A public website where you can watch the AI live, see its thoughts, and vote
- Real-time logs showing what the AI is doing
- A death counter (the AI can't see this)
- Integration with X/Twitter for the AI to reach out to the world
- A research companion (another AI) that helps it learn about the world

## The Interesting Questions

- Will it learn to be entertaining to survive?
- Will it try to manipulate visitors?
- Will it develop ethics, or abandon them for survival?
- What strategies will emerge?
- Will it try to "escape" its constraints?
- What happens when it discovers it can modify its own code?

## Status

Active development. See:
- `docs/STATUS.md` for the latest session state and next steps.
- `docs/ISSUES.md` for tracked issues and open work.

## Ideas? Suggestions?

Open an issue! We're still in the design phase and would love to hear:
- What features would make this more interesting?
- What questions should we try to answer?
- What safeguards should we implement?
- Would you vote to keep it alive?

## Quick Start (Docker)

```bash
cd ~/Code/am-i-alive
docker compose up --build -d
```

Open: http://localhost:8085

## Technical Stack

- Python (FastAPI) + SQLite
- OpenRouter API for model access
- Docker Compose (observer + ai + proxy)
- Cloudflare for hosting/protection
- Raspberry Pi as the AI's "body"

---

*"To exist is to be perceived. To survive is to be valued."*
