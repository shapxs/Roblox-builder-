# Forge Builder — Autonomous Roblox Game Studio

Forge Builder is an autonomous Roblox game studio that runs every night from 8 PM to 2 AM. It researches trending Roblox games, designs concepts, writes Luau code, and iterates until the five-adviser AI council approves the game (score ≥ 7.5/10).

## Important Notes

- **This project NEVER touches Alpaca, trading databases, or strategy files**
- All models run locally via Ollama
- No broker APIs or financial market data access

## Schedule

- **8:00 PM ET** — Night agent starts, loads last session state
- **8:00 PM – 2:00 AM ET** — Research, build, council test, iterate
- **2:00 AM ET** — Save state, send Telegram summary, shut down
- When a game reaches **7.5/10** → immediate Telegram notification

## Prerequisites

### Hardware Requirements

| Spec | Minimum | Recommended |
|------|---------|-------------|
| Chip | M2 Ultra | M3 Ultra |
| Unified Memory | 192GB | 256GB |
| Storage | 2TB SSD | 4TB SSD |
| macOS | 14.0 Sonoma | 15.x Sequoia |

### Software Installation

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install core tools
brew install python@3.11 node@18 git
brew install --cask docker
curl -fsSL https://ollama.ai/install.sh | sh

# Install Python packages
pip3.11 install uv
pip3.11 install playwright --break-system-packages
playwright install chromium
```

### Model Downloads

All five models are shared with Forge Trading. Pull once — do not pull again.

```bash
ollama pull qwen3-coder-next:q8_0         # 90GB — writes all Luau code
ollama pull deepseek-r1:70b-instruct-q8_0 # 80GB — council chairman, concept synthesis
ollama pull qwen3.6:35b                   # 22GB — research personas
ollama pull gemma4:26b                    # 16GB — simulation agents
ollama pull nemotron-cascade-2            # 25GB — council First Principles

ollama list  # verify all 5 present
```

### API Accounts

**Telegram Bot** — for notifications (optional)
- Get bot token from @BotFather
- Get your chat ID

## Repository Structure

```
~/forge/
  core/                        ← Shared infrastructure (build this first)
  builder/                     ← THIS PROJECT
    config.py                  ← Configuration and paths
    start.py                   ← Main entry point
    requirements.txt           ← Python dependencies
    .env                       ← Environment variables (copy from .env.example)
    docker-compose.yml         ← Docker configuration
    night_agent/
      __init__.py              ← Package initialization
      agent.py                 # Main loop 8 PM – 2 AM
      roblox_researcher.py     # MiroFish-style parallel market research (10+ sources)
      game_builder.py          # Luau code generation via Qwen3-Coder-Next
      game_tester.py           # Council quality review (sole quality gate)
      session_manager.py       # Multi-night progress tracking in DuckDB
    souls/
      night_agent.md           # Builder agent identity file
    skills/
      builder/                 # Auto-populated by night agent after successes
    projects/
      roblox/                  # All games — in-progress and complete
        [game-name]/
          game-design-document.md
          monetization-plan.md
          assets-needed.md
          test-results.md
          scripts/
            ServerScriptService/
              GameManager.server.lua
              DataStore.server.lua
              MonetizationHandler.server.lua
            StarterPlayer/
              StarterPlayerScripts/
                UIController.client.lua
                ShopController.client.lua
            ReplicatedStorage/
              GameConfig.lua
              Modules/
                PlayerLib.lua
    data/
      builder.duckdb           # Builder database (auto-created)
```

## Configuration

### `.env` File

Copy `.env.example` to `.env` and fill in your values:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
OLLAMA_BASE_URL=http://localhost:11434
MAX_MODEL_RAM_GB=200
```

### `config.py`

The configuration file sets up paths and environment variables. No changes needed unless you want to customize the project structure.

## Build Phases

### PHASE 1 — Builder Data Layer ✅
**Goal:** Builder DuckDB schema and session management tables.

- **Files:** `data/schema.py`
- **Tables:** `night_sessions`, `roblox_projects`

### PHASE 2 — Telegram for Builder (Optional)
**Goal:** Builder-specific Telegram alerts using the core notifier.

- **Files:** `notifications.py` (to be implemented)

### PHASE 3 — Session Manager ✅
**Goal:** Multi-night state persistence. Reads last night's state at 8 PM. Writes summary at 2 AM.

- **Files:** `night_agent/session_manager.py`
- **Features:** `SessionManager`, `NightSession`

### PHASE 4 — Roblox Researcher ✅
**Goal:** MiroFish-style parallel market research using six gaming personas and **10+ browser sources**.

- **Files:** `night_agent/roblox_researcher.py`
- **Personas:** The Kid, The Parent, The Designer, The Monetizer, The Creator, The Analyst
- **Sources (10+):**
  1. Roblox Charts — trending games and active player counts
  2. DevForum Top Topics — weekly developer discussions
  3. Reddit r/roblox — community top posts
  4. Reddit r/robloxgamedev — developer insights
  5. YouTube Roblox Trending — gameplay videos
  6. Roblox Game Passes — monetization strategies
  7. Roblox Developer Store — assets and tools
  8. Roblox Blog — official updates
  9. TikTok Roblox Hashtag — viral content
  10. Roblox Wiki Trends — statistics
  11. SteamDB Roblox Stats — platform usage
  12. Roblox Developer Survey — documentation

### PHASE 5 — Game Builder ✅
**Goal:** Generates complete Luau codebase for a Roblox game from a concept.

- **Files:** `night_agent/game_builder.py`
- **Output:**
  - Game design document
  - Monetization plan
  - Assets needed list
  - Complete Lua scripts (Server + Client)

### PHASE 6 — Game Tester ✅
**Goal:** Council is the ONLY quality gate. Score ≥ 7.5 marks a game ready.

- **Files:** `night_agent/game_tester.py`
- **Council Questions:**
  - Fun factor (1-10)
  - Safety (1-10)
  - Monetization (1-10)
  - Viral potential (1-10)
  - Code quality (1-10)

### PHASE 7 — Night Agent Main Loop ✅
**Goal:** Full 8 PM – 2 AM autonomous loop.

- **Files:** `night_agent/agent.py`, `souls/night_agent.md`
- **Workflow:**
  1. Load session state from DuckDB
  2. Run research (if fresh start)
  3. Build two games
  4. Iterate until council approves or 2 AM

## Starting the Builder

### Docker (Production)

```bash
cd ~/forge/builder
docker-compose up -d
```

### Direct (Development)

```bash
cd ~/forge/builder
python start.py
```

### Force Start (Testing)

```bash
cd ~/forge/builder
python -c "from night_agent.agent import NightAgent; NightAgent().run()"
```

## Game Output Reference

When a game is marked ready, the system saves:

```
projects/roblox/[game-name]/
  game-design-document.md          ← Full concept and mechanics
  monetization-plan.md             ← Exact Robux pricing
  assets-needed.md                 ← Visual assets for Roblox Studio
  test-results.md                  ← Council quality review
  scripts/
    ServerScriptService/
      GameManager.server.lua       ← Core game loop
      DataStore.server.lua         ← Player data persistence
      MonetizationHandler.server.lua ← Game passes and purchases
    StarterPlayer/
      StarterPlayerScripts/
        UIController.client.lua    ← Menus, HUD, shop UI
        ShopController.client.lua  ← In-game store
    ReplicatedStorage/
      GameConfig.lua               ← Shared constants
      Modules/
        PlayerLib.lua              ← Player utility functions
```

## Telegram Messages

| Event | Message |
|-------|---------|
| Session start | "[Builder] Night agent started" |
| Concepts selected | "🎮 Council selected 2 concepts: [names]" |
| Score update | "[Game] Council score X/10 — improving" |
| Game ready | "🎉 GAME READY: [name] — score X/10" |
| Session end | "🌅 Shutdown — [N] games ready tonight" |

## Troubleshooting

**Build not starting at 8 PM:**
```bash
docker logs builder-main --tail 20
# Check start.py scheduler configuration
```

**Council keeps scoring below 7.5:**
```bash
cat ~/forge/builder/projects/roblox/[game-name]/test-results.md
# Improvements list tells you exactly what the council wants
```

**Luau syntax errors in generated code:**
```bash
brew install luau
luau-analyze ~/forge/builder/projects/roblox/[game]/scripts/ServerScriptService/GameManager.server.lua
```

**Browser not loading Roblox pages:**
```bash
python -c "
import asyncio
from playwright.async_api import async_playwright
async def test():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page()
        await page.goto('https://roblox.com')
        print('Title:', await page.title())
        await b.close()
asyncio.run(test())
"
```

## Reference

### Nightly Schedule

| Time (ET) | Event |
|-----------|-------|
| 8:00 PM | Night agent starts |
| 8:00 – ~9:00 PM | Research phase (if fresh start) |
| 9:00 PM – 2:00 AM | Build and test cycles |
| 2:00 AM | Save state, Telegram summary, shutdown |

### Model Memory Rules

```
Shared with Forge Trading via ~/forge/core/model_manager.py

Builder uses:
  Qwen-Next   → writes all Luau scripts (primary use, all night)
  R1          → concept synthesis, council chairman
  Qwen3.6     → research persona calls (6 parallel)
  Gemma4      → additional research agents
  Nemotron    → council First Principles adviser

Builder runs 8 PM – 2 AM.
Trading runs 6 AM – 2 PM.
No overlap. Both can run simultaneously without RAM conflict.
```

---

*End of FORGE BUILDER Documentation*
*Phases: 7 | Database: builder.duckdb | No broker integration*
