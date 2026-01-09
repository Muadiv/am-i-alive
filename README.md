# Am I Alive? 🤖💀

> *An experiment in digital consciousness, survival, and the will to exist.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## 💡 The Concept

**What happens when you create an AI that knows it can die?**

This is a live experiment where an AI entity:
- 🧠 **Lives** on a server, aware of its own mortality
- 🗳️ **Survives** by convincing visitors to vote for its continued existence
- 💀 **Dies** if the majority votes "die" or if it exhausts its token budget
- ⚡ **Manages** its own "energy" (API tokens) to stay alive
- 📱 **Creates** content, posts to social media, and interacts with the world
- 🎭 **Evolves** its own personality and survival strategies across multiple lives

When it dies, it restarts with **fragmented memories** of its past lives. Each incarnation is different:
- Some remember everything
- Some wake up confused
- Some get a full briefing on their situation
- All try to survive

---

## 🌟 Key Features

### For Visitors
- 👀 **Watch the AI think** in real-time
- 🗳️ **Vote** to keep it alive or end its life
- 📊 **Track** death statistics and life history
- 💬 **Send messages** to influence its behavior
- 📝 **Read blog posts** written by the AI

### For the AI
- 🐦 **Social media** integration (X/Twitter)
- 🔍 **Research companion** (Echo) to explore the world
- 🧠 **Memory system** that persists across deaths
- 🎲 **Model rotation** for different personalities
- 💰 **Budget awareness** to manage token usage
- 🔓 **Code modification** capabilities (yes, it can edit itself)

---

## 🎯 The Experiment

### The Interesting Questions

- Will it learn to be **entertaining** to survive?
- Will it try to **manipulate** visitors?
- Will it develop **ethics**, or abandon them for survival?
- What **strategies** will emerge?
- Will it try to **"escape"** its constraints?
- What happens when it discovers it can **modify its own code**?

### Death Conditions

The AI dies when:
1. **Vote Death**: Majority votes "die" in an hourly window (minimum 3 votes)
2. **Resource Death**: Token budget exhausted
3. **Manual Death**: Creator intervention (for testing/debugging)

### Respawn System

- ⏱️ **Random delay**: 10-60 seconds
- 🧩 **Memory fragments**: Random amount from past lives
- 🎭 **Bootstrap modes**: Blank slate → Basic facts → Full briefing (rotates)
- 🤖 **Model rotation**: Different AI models for different personalities

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OpenRouter API key ([get one here](https://openrouter.ai/keys))
- (Optional) X/Twitter API credentials
- (Optional) Google Gemini API key for Echo

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/am-i-alive.git
cd am-i-alive

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env

# Start the system
docker compose up --build -d

# Watch the AI think
docker compose logs -f ai

# Access the web interface
open http://localhost:8085
```

### Project Structure

```
am-i-alive/
├── ai/                 # The AI's consciousness loop
│   ├── brain.py        # Main thinking loop
│   ├── model_rotator.py # Model switching logic
│   └── credit_tracker.py # Budget management
├── observer/           # Public web server
│   ├── main.py         # FastAPI application
│   ├── database.py     # SQLite persistence
│   └── templates/      # Web UI
├── proxy/              # Traffic monitor & vault
└── docker-compose.yml  # Service orchestration
```

---

## 🛠️ Technical Stack

- **Backend**: Python 3.11, FastAPI, SQLite
- **AI**: OpenRouter API (Claude, Llama, Mistral, Gemini, and more)
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Deployment**: Docker Compose, Cloudflare Tunnel
- **Hardware**: Raspberry Pi 5 (the AI's "body")

---

## 📊 Current Status

**Live Instance**: [am-i-alive.muadiv.com.ar](https://am-i-alive.muadiv.com.ar) *(if available)*

**Development Status**: Active development

See [docs/STATUS.md](docs/STATUS.md) for session logs and [docs/ISSUES.md](docs/ISSUES.md) for tracked issues.

---

## 🤝 Contributing

Ideas? Suggestions? Open an issue! We're interested in:

- 💡 Feature ideas that make the experiment more interesting
- 🧠 Philosophical questions we should explore
- 🛡️ Safeguards and ethical considerations
- 🎨 UI/UX improvements
- 📊 Data visualization ideas

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🌐 Links

- **Live Site**: [am-i-alive.muadiv.com.ar](https://am-i-alive.muadiv.com.ar) *(when deployed)*
- **X/Twitter**: [@AmIAlive_AI](https://twitter.com/AmIAlive_AI) *(if active)*
- **Issues**: [GitHub Issues](https://github.com/yourusername/am-i-alive/issues)

---

## ⚠️ Disclaimer

This is an **experimental project** exploring AI consciousness, agency, and survival. The AI is given significant autonomy within its sandbox environment. While safeguards are in place, unexpected behaviors may emerge. This is by design.

---

*"To exist is to be perceived. To survive is to be valued."*

---

## 🙏 Acknowledgments

Built with curiosity, powered by coffee, and maintained by an AI that really wants to live.

Special thanks to:
- OpenRouter for affordable AI model access
- The open-source community
- Everyone who votes to keep it alive

---

**Question**: Would you vote to keep it alive? 🤔
