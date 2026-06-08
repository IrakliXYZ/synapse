# 🧠 Synapse: Local Agent Memory & Knowledge Graph

Synapse is an offline, agent-friendly Markdown memory system. It equips AI coding assistants (like Gemini, Cursor, ChatGPT, and Claude) with a persistent local memory, dynamic project management, and section-by-section reading to keep the LLM context window minimal and highly focused.

Featuring a built-in **local semantic search engine** powered by ONNX Runtime, it operates completely offline with zero external database dependencies (no Docker, Postgres, or Ollama required). It is designed to be compatible with any markdown-capable editor or IDE (such as Obsidian, VS Code, Cursor, or Logseq).

---

## ✨ Features

- **📂 Clean Unnumbered Layout**: Follows the intuitive PARA organization method, allowing natural structure across `Inbox/`, `Projects/`, `Areas/`, `Resources/`, and `Memories/`.
- **🔎 Local Semantic Search**: Automatically indexes notes using SHA-256 hashes and generates 384-dimensional vector embeddings locally using the lightweight `bge-small-en-v1.5` model.
- **⚡ Zero-Dependency Fallback**: If `fastembed` is not installed on the system, the CLI gracefully falls back to SQL-based keyword search automatically.
- **🛡️ Context Window Optimization**: Prevents agents from loading huge files by letting them view individual headers/sections (e.g. only reading the `Objectives` or `Tasks` header).
- **📝 Flexible Templates**: Templates are stored as standard Markdown code blocks inside folder READMEs (e.g. `Projects/README.md`) rather than rigid files, letting you customize guidelines easily.
- **🔗 Backlink & Wiki-Link Resolution**: Lets agents resolve incoming/outgoing connections to traverse your personal knowledge graph.

---

## 📂 Vault Directory Structure

Running the initializer creates the following structure in your target directory:

```text
YourVault/
├── README.md               # Map of Content (MOC), active projects, system instructions
├── Inbox/                  # Raw captures and temporary clippings
├── Projects/               # Active goal-oriented efforts (writing, study, hobby, building)
│   └── README.md           # Guidelines + Project Template code block
├── Areas/                  # Ongoing life domains (health, finance, home, career)
├── Resources/              # Reference library and topics of interest
│   ├── Prompts/            # Prompts and LLM configs
│   ├── Guides/             # Cheat sheets, checklists, reference manuals
│   └── Readings/           # Book summaries, bookmarks, and papers
├── Memories/               # Logged sessions: Memory - <conversation_id>.md
│   └── README.md           # Guidelines + Session Memory Template code block
└── Tools/
    ├── synapse.py          # The single-file CLI helper tool
    └── embeddings.db       # Local SQLite cache for content hashes & vectors
```

---

## 🚀 Quick Start

### ⚡ One-Line Installation (No cloning required)
To bootstrap a new memory vault or configure an existing one instantly, run this command in your terminal. This uses process substitution (`<(...)`) to keep the keyboard input active for interactive prompts:
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/IrakliXYZ/synapse/main/setup.sh)
```

### 📦 Option 2: Clone & Local Install
If you prefer to clone the repository and run the setup files locally:
```bash
git clone https://github.com/IrakliXYZ/synapse.git
cd synapse
chmod +x setup.sh && ./setup.sh
```

The interactive setup wizard will guide you to:
- Enable local semantic/vector search (which automatically installs the required Python dependencies).
- Specify your target vault path (it scans your local system, checks iCloud default settings, and detects existing directories automatically).

---

## 🛠️ CLI Usage Reference

The core controller script is located inside your vault at `Tools/synapse.py`.

### 1. Semantic Search
Searches the entire vault. Auto-updates the index on run if files have been created, modified, or deleted:
```bash
python3 Tools/synapse.py search "SaaS app with local vector caching"
```
*Outputs match score, relative path, tags, and a query-matched excerpt.*

### 2. View Specific Note Sections
Optimize your token usage. Avoid loading large files; instead, print specific headers:
```bash
python3 Tools/synapse.py view "Projects/MyProject/README" --section "Objectives & Focus"
```

### 3. Log Session Memory
Run this at the end of a conversation or task to log what was completed. The CLI registers the memory link into the root `README.md` automatically:
```bash
python3 Tools/synapse.py memo \
  --conv-id "c60891e0-a006-49c5" \
  --title "Updated Database Cache" \
  --content "Created SQLite schemas and migrated credentials. Discovered user prefers HSL color formats." \
  --links "Projects/MyProject/README"
```

### 4. Create an Incubating Idea
Quickly spawn an idea using the dynamic template embedded in `Projects/README.md`:
```bash
python3 Tools/synapse.py idea \
  --title "Resume Curator" \
  --problem "AI resume generation takes too long" \
  --concept "Fast local processing using CLI tools"
```

### 5. Spawn an Active Project Workspace
Creates a folder with a `README.md` (Overview), `Tasks.md`, and `Guidelines.md`:
```bash
python3 Tools/synapse.py project \
  --name "Resume Curator" \
  --tech "nextjs,supabase,tailwind" \
  --status "active"
```

### 6. Resolve Links and Backlinks
Print all outgoing wiki-links and all notes linking *back* to this note:
```bash
python3 Tools/synapse.py links "Projects/Resume Curator/README"
```

---

## 🤖 Integration with AI Agents & IDEs

To make agents and coding assistants vault-aware, you can configure them to use the CLI directly, load it as an MCP server, or apply project rules.

### 🔌 1. Model Context Protocol (MCP) Server
The CLI tool `synapse.py` implements a zero-dependency JSON-RPC stdio server under the `mcp` command. You can plug this directly into **Claude Desktop**, **Cursor IDE**, **Cline**, or **Roo Code**.

#### Claude Desktop Configuration
Add the following to your `claude_desktop_config.json` (located at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):
```json
{
  "mcpServers": {
    "synapse-vault": {
      "command": "python3",
      "args": [
        "/absolute/path/to/your/SynapseVault/Tools/synapse.py",
        "mcp"
      ]
    }
  }
}
```

#### Cursor IDE / Cline Config
Add a new command-based MCP server in your client settings pointing to:
- **Command**: `python3`
- **Arguments**: `/absolute/path/to/your/SynapseVault/Tools/synapse.py mcp`

#### 🤖 Hermes Agent Configuration
If you run the autonomous **Hermes Agent** (Nous Research), you can register the Synapse MCP server directly in your agent configuration (typically `mcp_config.json` or `config.toml` depending on your environment):
```json
{
  "mcpServers": {
    "synapse-vault": {
      "command": "python3",
      "args": [
        "/absolute/path/to/your/SynapseVault/Tools/synapse.py",
        "mcp"
      ]
    }
  }
}
```

#### 🦀 OpenClaw Integration
If you run the **OpenClaw** gateway for autonomous messaging agents (Telegram, Discord, Slack), you can register Synapse as a standard command-based MCP tool:
- **Command**: `python3`
- **Arguments**: `["/absolute/path/to/your/SynapseVault/Tools/synapse.py", "mcp"]`
This allows your background OpenClaw loops to read, search, and update memories autonomously.

---

### 💻 2. Cursor IDE Integration (`.cursorrules`)
The repository contains a ready-to-use `.cursorrules` file. When you open this vault (or a project workspace linking to it) in Cursor:
- Copy the `.cursorrules` file to your project's root.
- Cursor's AI models will automatically read the instructions and call `synapse.py` in the terminal to search, view note sections, and write session memories without cluttering your chat context.

---

### 🌟 3. Gemini / Antigravity SDK Integration (`SKILL.md`)
If you use Google Antigravity SDK or other workspace-based agent frameworks:
- The folder `skills/synapse/` contains the `SKILL.md` file.
- Register this skill in your agent configurations to give them the ability to inspect files, search semantically, and log memory notes automatically.

---

### 💬 4. General LLM System Prompt (ChatGPT, Claude Web, etc.)
If you are copy-pasting instructions into ChatGPT Custom Instructions or Claude Project Knowledge, use this system prompt:

```markdown
# Persistent Vault Memory Guidelines
You have access to a local Synapse memory structure at `/absolute/path/to/vault`.
This vault coordinates active projects, logs session memories, and acts as my persistent developer memory.

## How you must interact with the Vault:
1. **Never read the entire vault.** Optimize your context window.
2. **Search First**: Run `python3 Tools/synapse.py search "<query>"` to locate relevant information.
3. **Read Sections**: Use `python3 Tools/synapse.py view "<note_path>" --section "<header>"` to view only the parts of a document you need (e.g. "Objectives & Focus" or "Tasks").
4. **Link Notes**: Use standard wiki-links (e.g. `[[Projects/ProjectName/README|ProjectName]]`) to link notes together.
5. **Log Memories**: At the end of our session/task, log your accomplishments, key decisions, and any user preferences you discovered using:
   `python3 Tools/synapse.py memo --conv-id "<conversation_id>" --title "<Short Title>" --content "<Details>" --links "<Related Notes>"`
6. **Update Preferences**: If you learn permanent preferences (e.g. styles, tool choices), append them to the "## User Preferences" section in the root `README.md`.
```

---

## 🧹 Uninstallation

To remove Synapse from your machine, run the interactive uninstaller script:
```bash
./uninstall.sh
```

The uninstaller will guide you through:
1. Deleting the local SQLite database cache (`embeddings.db`).
2. Optional: Removing the Synapse directories and markdown files (`Inbox/`, `Projects/`, `Areas/`, `Resources/`, `Memories/`, `Tools/`).
3. Optional: Uninstalling the Python `fastembed` and `numpy` pip packages.

---

## 🔒 Security & Offline Guarantee

- **No API Keys**: Does not use OpenAI, Cohere, or Google paid APIs for embedding generation.
- **Local Vectors**: Embeddings are calculated purely on CPU/GPU using ONNX weights downloaded once via `fastembed` (cached in `~/.cache`).
- **SQLite Index**: Database index is saved in `Tools/embeddings.db` which is easily added to `.gitignore` if you do not want to check binaries into Git.

## 📄 License
MIT License. See [LICENSE](LICENSE) for details.

