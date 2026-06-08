#!/usr/bin/env python3
import os
import sys
import re
import argparse
import datetime
import hashlib
import sqlite3
import json
from pathlib import Path

DEFAULT_VAULT_PATH = "~/SynapseVault"

try:
    from fastembed import TextEmbedding
    import numpy as np
    FASTEMBED_AVAILABLE = True
except ImportError:
    FASTEMBED_AVAILABLE = False

# --- Default Fallback Templates (Minimal & Flexible) ---

TEMPLATES = {
    "Template - Project.md": """---
status: {status} # planning, active, paused, done
tags: {tags}
created: {date}
---
# Project - {title}

{body}
""",

    "Template - Resource.md": """---
type: reference # reference, guide, reading, prompt
tags: {tags}
created: {date}
---
# Resource - {title}

{body}
""",

    "Template - Session Memory.md": """---
date: {date}
conversation_id: {conv_id}
context: {context}
tags: [session-memory]
---
# Session Memory - {title}

## Summary of Updates
{content}

## Key Decisions & Choices
<!-- What was decided and why? -->

## Discovered Preferences & Insights
<!-- What preferences did the user express? -->

## Next Steps / Pending Tasks
- [ ] Continue next session tasks
"""
}

# --- Folder README Contents ---

README_CONTENTS = {
    "Inbox": "# Inbox Folder\n\nTemporary staging area for raw notes, quick capture ideas, links, and clips. Sort these regularly.",
    
    "Projects": """# Projects Folder

Contains active efforts with specific goals (e.g. creative writing, research, home projects, software, hobbies). Every project has its own folder containing a `README.md` (which acts as the project overview).

## Guidelines for Agents
1. **Dynamic Structure**: Format the body dynamically depending on the project's size, phase, and needs. Do not feel bound to a rigid layout.
2. **YAML Frontmatter**: Always include status, tags, and creation date.
3. **Note Linking**: Link to areas (`[[Areas/...]]`) and other relevant topics to maintain the knowledge graph.

## Project Template

```markdown
---
status: {status} # planning, active, paused, done
tags: {tags}
created: {date}
---
# Project - {title}

{body}
```""",

    "Areas": """# Areas Folder

Contains long-term domains of interest or ongoing responsibilities that require standard maintenance (e.g. Finance, Health, Home, Career, Hobbies).

Every area is represented as a subfolder or markdown note linking to relevant projects and resources.""",
    
    "Resources": """# Resources Folder

Reference library and topics of ongoing interest. Contains prompts, cheat sheets, bookmarks, guides, and learning notes.

## Resource Template

```markdown
---
type: reference # reference, guide, reading, prompt
tags: {tags}
created: {date}
---
# Resource - {title}

{body}
```""",
    
    "Resources/Prompts": "# Prompts Folder\n\nCustom agent prompts, system prompt snippets, and LLM behavior configs.",
    
    "Resources/Guides": "# Guides Folder\n\nReference guides, checklists, cheat sheets, and guidelines.",
    
    "Resources/Readings": "# Readings Folder\n\nSummaries of papers, articles, book notes, and other learning content.",
    
    "Memories": """# Memories Folder

Contains conversation logs and memory summaries for individual agent sessions.

## Guidelines for Agents
1. **Session Memory**: At the end of every session, log a memory summary using the template. Outline changes, key decisions, and user preferences discovered.
2. **Wiki-linking**: Link memories to active projects (`[[Projects/...]]`) and areas (`[[Areas/...]]`).
3. **User Preferences**: Update the root `README.md` under `## User Preferences` if you discover persistent user preferences (e.g. style guides, workflow methods).

## Session Memory Template

```markdown
---
date: {date}
conversation_id: {conv_id}
context: {context}
tags: [session-memory]
---
# Session Memory - {title}

## Summary of Updates
{content}

## Key Decisions & Choices
<!-- What was decided and why? -->

## Discovered Preferences & Insights
<!-- What preferences did the user express? -->

## Next Steps / Pending Tasks
- [ ] Continue next session tasks
```"""
}

# --- Consolidated Root README.md (Overview + MOC + Preferences + Instructions) ---

CONSOLIDATED_README = """# Irakli's Synapse Memory & Workspace

This Synapse Memory Vault is your digital brain, designed to organize projects, areas of interest, reference notes, and act as a persistent memory for AI agents.

## Folder Index
1. **[[Inbox/README|Inbox]]**: Staging area for quick captures and unprocessed clippings.
2. **[[Projects/README|Projects]]**: Active goal-oriented efforts (writing, building, studying).
3. **[[Areas/README|Areas]]**: Ongoing domains of life and responsibilities (health, finance, hobbies).
4. **[[Resources/README|Resources]]**: Reference library, guides, prompt books, and reading summaries.
5. **[[Memories/README|Memories]]**: Conversation logs and memory summaries for individual agent sessions.

---

## User Preferences
<!-- Permanent traits, coding preferences, and guidelines learned about the user across conversations. Update this whenever a new preference is confirmed. -->
- **Preferred Languages**: JavaScript/TypeScript, Python.
- **Preferred Styles**: Vanilla CSS, premium HSL palettes, smooth animations, zero-dependency CLI tools.

## Active Projects
<!-- Added automatically by synapse.py project -->

## Conversation History
<!-- Added automatically by synapse.py memo -->

## Environment & Hardware Setup
- OS: macOS
- Main Workspace: `/Users/irakli/.gemini/antigravity/scratch`

---

## Agent Instructions & Guidelines

Welcome, AI Agent. This Synapse memory vault serves as the persistent memory and knowledge graph for our work, designed to be utilized by both interactive assistants (e.g. Cursor, Claude Desktop) and autonomous systems (e.g. Hermes, OpenClaw). To maintain structure and optimize context window limits, you **must** adhere to the following rules when interacting with this vault.

### 1. Reading Context (Context Window Optimization)
- **Do not read the entire vault.** Use the `synapse.py search` command to locate notes.
- **Section-Level Reading**: Use the `synapse.py view` command with the `--section` flag to read specific parts of a note (e.g., `Tasks` or `Code Guidelines`) rather than loading the whole file. This keeps your token count low and maintains high focus.

### 2. Writing and Updating Memories
- **At the end of every task or conversation**: Create or append to a conversation memory note in `Memories/Memory - <conversation_id>.md` using `synapse.py memo`.
- **Always Link Notes**: When logging memories, link them to the active projects or areas they relate to using standard wiki-links (e.g., `[[Projects/MyProject/README|MyProject]]`).
- **Update User Preferences**: If you learn a permanent preference about the user, update the `README.md` under `## User Preferences`.

### 3. Guidelines & Standards
- When working on project files, always refer to `Projects/<Project Name>/Guidelines.md` (or relevant project guidelines) to check if there are specific rules, styles, or patterns expected. Do not invent new structures that contradict these rules.
"""

# --- CLI Helper Functions ---

def get_vault_path(args):
    path_str = args.vault or os.environ.get("SYNAPSE_VAULT_PATH") or os.environ.get("OBSIDIAN_VAULT_PATH") or DEFAULT_VAULT_PATH
    expanded_path = os.path.expanduser(path_str)
    return os.path.abspath(expanded_path)

def load_template(vault_path, folder, section_name, template_key):
    readme_path = os.path.join(vault_path, folder, "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            lines = content.split('\n')
            in_section = False
            section_lines = []
            header_pattern = r'^(#{1,6})\s+(.*)$'
            target_level = 0
            
            for line in lines:
                match = re.match(header_pattern, line)
                if match:
                    level = len(match.group(1))
                    title = match.group(2).strip().lower()
                    if in_section:
                        if level <= target_level:
                            break
                    elif section_name.lower() in title:
                        in_section = True
                        target_level = level
                elif in_section:
                    section_lines.append(line)
                    
            if in_section:
                section_text = '\n'.join(section_lines)
                code_match = re.search(r'```markdown\s*\n(.*?)\n```', section_text, re.DOTALL)
                if code_match:
                    return code_match.group(1)
        except Exception:
            pass
            
    # Fallback to hardcoded template
    return TEMPLATES.get(template_key)

def init_db(vault_path):
    db_dir = os.path.join(vault_path, "Tools")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "embeddings.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents (
        path TEXT PRIMARY KEY,
        title TEXT,
        tags TEXT,
        content TEXT,
        hash TEXT,
        embedding TEXT
    )
    """)
    conn.commit()
    conn.close()
    return db_path

def get_file_hash(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return hashlib.sha256(content.encode('utf-8')).hexdigest(), content
    except Exception:
        return "", ""

def update_index(vault_path, model=None):
    db_path = init_db(vault_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get indexed paths and hashes
    cursor.execute("SELECT path, hash FROM documents")
    db_docs = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Scan filesystem
    current_files = {}
    for root, dirs, files in os.walk(vault_path):
        if '.obsidian' in root.split(os.sep) or 'Tools' in root.split(os.sep):
            continue
        for file in files:
            if not file.endswith('.md') or file.startswith('Template - '):
                continue
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, vault_path)
            # Skip root README.md specifically
            if rel_path == 'README.md':
                continue
            current_files[rel_path] = file_path
            
    # Delete removed documents
    to_delete = set(db_docs.keys()) - set(current_files.keys())
    for rel_path in to_delete:
        cursor.execute("DELETE FROM documents WHERE path = ?", (rel_path,))
        print(f"Removed from index: {rel_path}")
        
    # Identify additions and updates
    to_update = []
    for rel_path, file_path in current_files.items():
        file_hash, content = get_file_hash(file_path)
        if not file_hash:
            continue
        if rel_path not in db_docs or db_docs[rel_path] != file_hash:
            to_update.append((rel_path, file_path, file_hash, content))
            
    if to_update:
        if model is not None and FASTEMBED_AVAILABLE:
            print(f"Computing embeddings for {len(to_update)} note(s)...")
            contents = [item[3] for item in to_update]
            embeddings = list(model.embed(contents))
            
            for i, (rel_path, file_path, file_hash, content) in enumerate(to_update):
                title = os.path.basename(file_path)[:-3]
                
                # Parse tags from YAML frontmatter
                tags_list = []
                fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                if fm_match:
                    fm_text = fm_match.group(1)
                    for line in fm_text.split('\n'):
                        if ':' in line:
                            k, v = line.split(':', 1)
                            if k.strip() == 'tags':
                                v_val = v.strip()
                                if v_val.startswith('[') and v_val.endswith(']'):
                                    tags_list = [x.strip().strip("'\"") for x in v_val[1:-1].split(',')]
                                else:
                                    tags_list = [v_val]
                
                tags_str = ",".join(tags_list)
                vector_str = json.dumps(embeddings[i].tolist())
                
                cursor.execute("""
                INSERT OR REPLACE INTO documents (path, title, tags, content, hash, embedding)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (rel_path, title, tags_str, content, file_hash, vector_str))
                print(f"Indexed note: {rel_path}")
        else:
            # Fallback indexing (no vector)
            for rel_path, file_path, file_hash, content in to_update:
                title = os.path.basename(file_path)[:-3]
                tags_list = []
                fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                if fm_match:
                    fm_text = fm_match.group(1)
                    for line in fm_text.split('\n'):
                        if ':' in line:
                            k, v = line.split(':', 1)
                            if k.strip() == 'tags':
                                v_val = v.strip()
                                if v_val.startswith('[') and v_val.endswith(']'):
                                    tags_list = [x.strip().strip("'\"") for x in v_val[1:-1].split(',')]
                                else:
                                    tags_list = [v_val]
                tags_str = ",".join(tags_list)
                
                cursor.execute("""
                INSERT OR REPLACE INTO documents (path, title, tags, content, hash, embedding)
                VALUES (?, ?, ?, ?, ?, NULL)
                """, (rel_path, title, tags_str, content, file_hash))
                print(f"Indexed note (no embedding): {rel_path}")
                
    conn.commit()
    conn.close()

def init_vault(vault_path):
    print(f"Initializing Synapse Vault at: {vault_path}")
    
    # Create Directories
    dirs_to_create = [
        "Inbox",
        "Projects",
        "Areas",
        "Resources",
        "Resources/Prompts",
        "Resources/Guides",
        "Resources/Readings",
        "Memories",
        "Tools"
    ]
    
    for d in dirs_to_create:
        full_dir = os.path.join(vault_path, d)
        os.makedirs(full_dir, exist_ok=True)
        readme_path = os.path.join(full_dir, "README.md")
        if not os.path.exists(readme_path) and d != "Tools":
            content = README_CONTENTS.get(d, f"# {d.replace('_', ' ')} Directory\n\nAuto-generated folder for the agent memory workflow.\n")
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created folder and README: {d}/README.md")

    # Write root Consolidated README
    root_readme = os.path.join(vault_path, "README.md")
    if not os.path.exists(root_readme):
        with open(root_readme, 'w', encoding='utf-8') as f:
            f.write(CONSOLIDATED_README)
        print("Created root README.md")

    # Copy self to Tools/synapse.py
    self_path = os.path.abspath(__file__)
    target_tool_path = os.path.join(vault_path, "Tools", "synapse.py")
    try:
        with open(self_path, 'r', encoding='utf-8') as source:
            code = source.read()
        with open(target_tool_path, 'w', encoding='utf-8') as target:
            target.write(code)
        os.chmod(target_tool_path, 0o755)
        print("Deployed CLI tool copy to Tools/synapse.py")
    except Exception as e:
        print(f"Warning: Could not copy script to vault tools directory: {e}")

    # Initialize SQLite database structure
    init_db(vault_path)
    print("Vault initialization complete!")

def is_mcp_already_configured(config_path):
    if not os.path.exists(config_path):
        return False
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        mcp_servers = data.get("mcpServers", {})
        return "synapse-vault" in mcp_servers
    except Exception:
        return False

def write_mcp_configuration(config_path, script_path):
    try:
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = {}
        if "mcpServers" not in data:
            data["mcpServers"] = {}
        data["mcpServers"]["synapse-vault"] = {
            "command": "python3",
            "args": [script_path, "mcp"]
        }
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        sys.stderr.write(f"Error writing configuration at {config_path}: {e}\n")
        return False

def setup_mcp_config_wizard(vault_path):
    print("\n===============================================")
    print("🔌 Automated MCP Server Setup")
    print("===============================================")
    print("Synapse can automatically configure your local AI agents (Claude Desktop,")
    print("Cline, Roo Code) to connect to this vault's MCP server.\n")
    
    try:
        choice = input("Would you like to automatically configure MCP for your agents? [Y/n]: ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nSkipped.")
        return
        
    if choice not in ("", "y", "yes"):
        print("Skipping automatic MCP configuration.")
        return
        
    synapse_script_path = os.path.join(vault_path, "Tools", "synapse.py")
    home = os.path.expanduser("~")
    configs = []
    
    # 1. Claude Desktop
    claude_path = ""
    if sys.platform == "darwin":
        claude_path = os.path.join(home, "Library", "Application Support", "Claude", "claude_desktop_config.json")
    elif sys.platform.startswith("linux"):
        claude_path = os.path.join(home, ".config", "Claude", "claude_desktop_config.json")
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            claude_path = os.path.join(appdata, "Claude", "claude_desktop_config.json")
            
    if claude_path:
        configs.append({
            "name": "Claude Desktop",
            "path": claude_path
        })
        
    # 2. Cline (VS Code & Cursor)
    if sys.platform == "darwin":
        configs.append({
            "name": "Cline (VS Code)",
            "path": os.path.join(home, "Library", "Application Support", "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")
        })
        configs.append({
            "name": "Cline (Cursor)",
            "path": os.path.join(home, "Library", "Application Support", "Cursor", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")
        })
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            configs.append({
                "name": "Cline (VS Code)",
                "path": os.path.join(appdata, "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")
            })
            configs.append({
                "name": "Cline (Cursor)",
                "path": os.path.join(appdata, "Cursor", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")
            })
    elif sys.platform.startswith("linux"):
        configs.append({
            "name": "Cline (VS Code)",
            "path": os.path.join(home, ".config", "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")
        })
        configs.append({
            "name": "Cline (Cursor)",
            "path": os.path.join(home, ".config", "Cursor", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")
        })

    # 3. Roo Code (VS Code & Cursor)
    if sys.platform == "darwin":
        configs.append({
            "name": "Roo Code (VS Code)",
            "path": os.path.join(home, "Library", "Application Support", "Code", "User", "globalStorage", "roodev.roo-cline", "settings", "cline_mcp_settings.json")
        })
        configs.append({
            "name": "Roo Code (Cursor)",
            "path": os.path.join(home, "Library", "Application Support", "Cursor", "User", "globalStorage", "roodev.roo-cline", "settings", "cline_mcp_settings.json")
        })
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            configs.append({
                "name": "Roo Code (VS Code)",
                "path": os.path.join(appdata, "Code", "User", "globalStorage", "roodev.roo-cline", "settings", "cline_mcp_settings.json")
            })
            configs.append({
                "name": "Roo Code (Cursor)",
                "path": os.path.join(appdata, "Cursor", "User", "globalStorage", "roodev.roo-cline", "settings", "cline_mcp_settings.json")
            })
    elif sys.platform.startswith("linux"):
        configs.append({
            "name": "Roo Code (VS Code)",
            "path": os.path.join(home, ".config", "Code", "User", "globalStorage", "roodev.roo-cline", "settings", "cline_mcp_settings.json")
        })
        configs.append({
            "name": "Roo Code (Cursor)",
            "path": os.path.join(home, ".config", "Cursor", "User", "globalStorage", "roodev.roo-cline", "settings", "cline_mcp_settings.json")
        })

    available_targets = []
    for conf in configs:
        parent_dir = os.path.dirname(conf["path"])
        if os.path.exists(conf["path"]) or os.path.exists(parent_dir):
            available_targets.append(conf)

    if not available_targets:
        print("\nNo supported agent configurations (Claude Desktop, Cline, or Roo Code) were detected on your machine.")
        print("Please configure your MCP settings manually by pointing your client to:")
        print(f"  Command: python3\n  Arguments: ['{synapse_script_path}', 'mcp']")
        return

    print("Detected the following agents:")
    for idx, target in enumerate(available_targets, 1):
        status = "[Already configured]" if is_mcp_already_configured(target["path"]) else "[Not configured]"
        print(f"  [{idx}] {target['name']} {status}")
    print(f"  [{len(available_targets)+1}] Configure all of them")
    print(f"  [{len(available_targets)+2}] Skip")

    try:
        sel = input(f"\nSelect which agent to configure [1-{len(available_targets)+2}]: ").strip()
        if not sel:
            return
            
        selected_targets = []
        if sel.isdigit():
            val = int(sel)
            if 1 <= val <= len(available_targets):
                selected_targets = [available_targets[val-1]]
            elif val == len(available_targets) + 1:
                selected_targets = available_targets
            else:
                print("Skipped configuration.")
                return
        else:
            print("Invalid selection. Skipped.")
            return

        for target in selected_targets:
            success = write_mcp_configuration(target["path"], synapse_script_path)
            if success:
                print(f"✔ Successfully configured MCP for {target['name']}.")
            else:
                print(f"❌ Failed to configure MCP for {target['name']}.")
                
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")

def search_vault(vault_path, query, tags=None):
    model = None
    if FASTEMBED_AVAILABLE:
        try:
            print("Loading local embedding model...")
            # fastembed automatically prints warning/logs to stderr; redirect to clean up if needed
            model = TextEmbedding()
        except Exception as e:
            print(f"Warning: Could not initialize fastembed model: {e}. Falling back to keyword search.")
            model = None
            
    # Auto-index
    update_index(vault_path, model)
    
    db_path = os.path.join(vault_path, "Tools", "embeddings.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tag_list = [t.strip().lower() for t in tags.split(',')] if tags else None
    
    # 1. Semantic Search (Embedding matches)
    if model is not None and FASTEMBED_AVAILABLE:
        query_vector = np.array(list(model.embed([query]))[0])
        
        cursor.execute("SELECT path, title, tags, content, embedding FROM documents WHERE embedding IS NOT NULL")
        rows = cursor.fetchall()
        
        results = []
        for r_path, r_title, r_tags_str, r_content, r_embed_str in rows:
            doc_tags = [t.strip().lower() for t in r_tags_str.split(',') if t.strip()]
            if tag_list and not all(t in doc_tags for t in tag_list):
                continue
                
            doc_vector = np.array(json.loads(r_embed_str))
            
            # Compute cosine similarity
            dot = np.dot(query_vector, doc_vector)
            norm_q = np.linalg.norm(query_vector)
            norm_d = np.linalg.norm(doc_vector)
            similarity = float(dot / (norm_q * norm_d)) if norm_q > 0 and norm_d > 0 else 0.0
            
            # Simple excerpt matching
            excerpt = ""
            query_lower = query.lower()
            body_lower = r_content.lower()
            idx = body_lower.find(query_lower)
            if idx != -1:
                start = max(0, idx - 40)
                end = min(len(r_content), idx + len(query) + 80)
                excerpt = r_content[start:end].replace('\n', ' ').strip()
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(r_content):
                    excerpt = excerpt + "..."
            else:
                excerpt = r_content[:120].replace('\n', ' ').strip() + "..."
                
            results.append({
                'path': r_path,
                'title': r_title,
                'tags': doc_tags,
                'score': similarity,
                'excerpt': excerpt
            })
            
        results.sort(key=lambda x: x['score'], reverse=True)
        conn.close()
        return results, True
        
    # 2. Fallback Keyword Search
    else:
        cursor.execute("SELECT path, title, tags, content FROM documents")
        rows = cursor.fetchall()
        
        query_lower = query.lower()
        results = []
        for r_path, r_title, r_tags_str, r_content in rows:
            doc_tags = [t.strip().lower() for t in r_tags_str.split(',') if t.strip()]
            if tag_list and not all(t in doc_tags for t in tag_list):
                continue
                
            match = False
            if query_lower in r_title.lower() or query_lower in r_content.lower():
                match = True
                
            if match:
                excerpt = ""
                body_lower = r_content.lower()
                idx = body_lower.find(query_lower)
                if idx != -1:
                    start = max(0, idx - 40)
                    end = min(len(r_content), idx + len(query) + 80)
                    excerpt = r_content[start:end].replace('\n', ' ').strip()
                    if start > 0:
                        excerpt = "..." + excerpt
                    if end < len(r_content):
                        excerpt = excerpt + "..."
                else:
                    excerpt = r_content[:120].replace('\n', ' ').strip() + "..."
                    
                results.append({
                    'path': r_path,
                    'title': r_title,
                    'tags': doc_tags,
                    'score': 1.0,
                    'excerpt': excerpt
                })
        conn.close()
        return results, False

def find_links(vault_path, note_name):
    target_file = None
    target_basename = note_name
    if note_name.endswith('.md'):
        target_basename = note_name[:-3]
        
    # Find target file
    for root, dirs, files in os.walk(vault_path):
        if '.obsidian' in root.split(os.sep):
            continue
        for file in files:
            rel = os.path.relpath(os.path.join(root, file), vault_path)
            if file.endswith('.md') and (file[:-3].lower() == target_basename.lower() or rel[:-3].lower() == target_basename.lower()):
                target_file = os.path.join(root, file)
                target_basename = file[:-3]
                break
        if target_file:
            break
            
    if not target_file:
        return None, None, f"Error: Note '{note_name}' not found."
        
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    outgoing_pattern = r'\[\[([^\]#|]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]'
    outgoing_matches = re.findall(outgoing_pattern, content)
    outgoing = sorted(list(set(outgoing_matches)))
    
    backlinks = []
    for root, dirs, files in os.walk(vault_path):
        if '.obsidian' in root.split(os.sep):
            continue
        for file in files:
            if not file.endswith('.md'):
                continue
            file_path = os.path.join(root, file)
            if file_path == target_file:
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            except Exception:
                continue
            backlink_pattern = r'\[\[\s*[^\]|]*?' + re.escape(target_basename) + r'\s*(?:#[^\]|]+)?(?:\s*\|[^\]]+)?\]\]'
            if re.search(backlink_pattern, file_content, re.IGNORECASE):
                backlinks.append(file[:-3])
                
    return outgoing, sorted(list(set(backlinks))), target_basename

def view_note(vault_path, note_name, section=None):
    target_file = None
    target_basename = note_name
    if note_name.endswith('.md'):
        target_basename = note_name[:-3]
        
    for root, dirs, files in os.walk(vault_path):
        if '.obsidian' in root.split(os.sep):
            continue
        for file in files:
            rel = os.path.relpath(os.path.join(root, file), vault_path)
            if file.endswith('.md') and (file[:-3].lower() == target_basename.lower() or rel[:-3].lower() == target_basename.lower()):
                target_file = os.path.join(root, file)
                break
        if target_file:
            break
            
    if not target_file:
        return f"Error: Note '{note_name}' not found."
        
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if not section:
        return content
        
    lines = content.split('\n')
    section_lines = []
    in_section = False
    target_level = 0
    section_lower = section.lower().strip()
    
    header_pattern = r'^(#{1,6})\s+(.*)$'
    
    for line in lines:
        match = re.match(header_pattern, line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip().lower()
            
            if in_section:
                if level <= target_level:
                    break
                else:
                    section_lines.append(line)
            elif title == section_lower:
                in_section = True
                target_level = level
                section_lines.append(line)
        elif in_section:
            section_lines.append(line)
            
    if not in_section:
        return f"Error: Section '{section}' not found in note '{note_name}'."
        
    return '\n'.join(section_lines)

def register_in_global_memory(vault_path, conv_id, title):
    global_mem_path = os.path.join(vault_path, "README.md")
    if not os.path.exists(global_mem_path):
        return
        
    with open(global_mem_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    target_header = "## Conversation History"
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    new_entry = f"- [[Memories/Memory - {conv_id}|Memory - {conv_id}]] - {title} ({date_str})"
    
    if target_header in content:
        parts = content.split(target_header, 1)
        lines = parts[1].split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip() != "":
                insert_idx = i
                break
        lines.insert(insert_idx, new_entry)
        updated_content = parts[0] + target_header + '\n' + '\n'.join(lines)
        with open(global_mem_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

def create_memo(vault_path, conv_id, title, content, links=None):
    mem_dir = os.path.join(vault_path, "Memories")
    os.makedirs(mem_dir, exist_ok=True)
    
    file_name = f"Memory - {conv_id}.md"
    file_path = os.path.join(mem_dir, file_name)
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    links_list = []
    if links:
        for l in links.split(','):
            l = l.strip()
            if not l:
                continue
            if not (l.startswith('[[') and l.endswith(']]')):
                l = f"[[{l}]]"
            links_list.append(l)
    links_formatted = ", ".join(links_list) if links_list else "None"
    
    if not os.path.exists(file_path):
        template_content = load_template(vault_path, "Memories", "Agent Memory Template", "Template - Agent Memory.md")
        
        new_content = template_content.replace("{date}", date_str)\
                                      .replace("{conv_id}", conv_id)\
                                      .replace("{project_link}", links_formatted)\
                                      .replace("{title}", title)\
                                      .replace("{content}", content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        register_in_global_memory(vault_path, conv_id, title)
        return f"Created new conversation memory file: Memories/Memory - {conv_id}.md"
    else:
        append_content = f"\n\n## Update ({now})\n**Related Links**: {links_formatted}\n\n{content}\n"
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(append_content)
        return f"Appended update to conversation memory file: Memories/Memory - {conv_id}.md"

def register_project_in_global_memory(vault_path, name, company):
    global_mem_path = os.path.join(vault_path, "README.md")
    if not os.path.exists(global_mem_path):
        return
        
    with open(global_mem_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    target_header = "## Active Projects"
    new_entry = f"- [[Projects/{name}/README|{name} Overview]] (Company: {company})"
    
    if target_header in content:
        parts = content.split(target_header, 1)
        lines = parts[1].split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip() != "":
                insert_idx = i
                break
        lines.insert(insert_idx, new_entry)
        updated_content = parts[0] + target_header + '\n' + '\n'.join(lines)
        with open(global_mem_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

def create_project(vault_path, name, company="Personal", tech="", status="planning", problem="", concept=""):
    project_dir = os.path.join(vault_path, "Projects", name)
    os.makedirs(project_dir, exist_ok=True)
    
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    readme_path = os.path.join(project_dir, "README.md")
    
    if not os.path.exists(readme_path):
        template_content = load_template(vault_path, "Projects", "Project Template", "Template - Project.md")
        
        tags_list = ['project']
        if status == "incubating":
            tags_list.append('idea')
        tags_str = "[" + ", ".join(tags_list) + "]"
        
        tech_list = []
        if tech:
            tech_list = [f"'{t.strip()}'" for t in tech.split(',') if t.strip()]
        tech_str = "[" + ", ".join(tech_list) + "]"
        
        body_parts = []
        if problem:
            body_parts.append(f"## Problem Statement\n{problem}\n")
        if concept:
            body_parts.append(f"## Core Concept\n{concept}\n")
        if not body_parts:
            body_parts.append("<!-- Describe goals, milestones, architecture, or research details dynamically -->\n")
        body_str = "\n".join(body_parts)
        
        new_content = template_content.replace("{status}", status)\
                                      .replace("{company}", company)\
                                      .replace("{tech}", tech_str)\
                                      .replace("{tags}", tags_str)\
                                      .replace("{date}", date_str)\
                                      .replace("{title}", name)\
                                      .replace("{body}", body_str)
                                      
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
    if status != "incubating":
        # Tasks.md
        tasks_path = os.path.join(project_dir, "Tasks.md")
        if not os.path.exists(tasks_path):
            tasks_content = f"# Tasks - {name}\n\n- [ ] Define project objective\n- [ ] Set up project structure\n"
            with open(tasks_path, 'w', encoding='utf-8') as f:
                f.write(tasks_content)
                
        # Guidelines.md
        guidelines_path = os.path.join(project_dir, "Guidelines.md")
        if not os.path.exists(guidelines_path):
            guidelines_content = f"""# Guidelines - {name}

## Objectives & Focus
<!-- Describe the main goals, scope, and key deliverables of this project -->

## Resources & Links
<!-- Key articles, books, folders, or web links -->

## Standards & Preferences
<!-- Any formatting rules, workflows, or styling preferences to keep in mind -->
"""
            with open(guidelines_path, 'w', encoding='utf-8') as f:
                f.write(guidelines_content)
                
    register_project_in_global_memory(vault_path, name, company)
    return f"Created project/idea workspace at: Projects/{name}/"

# --- Model Context Protocol (MCP) Stdio Server ---

def run_mcp_server(vault_path):
    sys.stderr.write("Starting Model Context Protocol (MCP) stdio server...\n")
    sys.stderr.flush()
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = handle_mcp_request(vault_path, request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"Error in MCP loop: {e}\n")
            sys.stderr.flush()

def handle_mcp_request(vault_path, request):
    msg_id = request.get("id")
    method = request.get("method")
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "agent-obsidian-vault",
                    "version": "1.0.0"
                }
            },
            "id": msg_id
        }
    
    elif method == "notifications/initialized":
        return None
        
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "search",
                        "description": "Search the vault notes semantically (using local ONNX embeddings) or with keywords, optionally filtering by tags.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "The search terms or question"},
                                "tags": {"type": "string", "description": "Optional comma-separated tags to filter by"}
                            },
                            "required": ["query"]
                        }
                    },
                    {
                        "name": "view",
                        "description": "View a note's full content or a specific header section (for token efficiency).",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "note": {"type": "string", "description": "The note title, file name, or path relative to the vault root"},
                                "section": {"type": "string", "description": "Optional header title to print specifically"}
                            },
                            "required": ["note"]
                        }
                    },
                    {
                        "name": "links",
                        "description": "Find outgoing links and incoming backlinks for a given note name.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "note": {"type": "string", "description": "Note title or path"}
                            },
                            "required": ["note"]
                        }
                    },
                    {
                        "name": "memo",
                        "description": "Log session memory or conversation summaries. Links them automatically into the root README.md index.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "conv_id": {"type": "string", "description": "Unique conversation or session ID"},
                                "title": {"type": "string", "description": "Title/short description of the memory"},
                                "content": {"type": "string", "description": "Summary details of what was completed, decisions, and preferences found"},
                                "links": {"type": "string", "description": "Optional comma-separated related note titles or paths"}
                            },
                            "required": ["conv_id", "title", "content"]
                        }
                    },
                    {
                        "name": "idea",
                        "description": "Create a new product idea note in Projects/ using templates.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Title of the product idea"},
                                "company": {"type": "string", "description": "Associated company", "default": "Personal"},
                                "problem": {"type": "string", "description": "Problem statement"},
                                "concept": {"type": "string", "description": "Core concept"}
                            },
                            "required": ["title"]
                        }
                    },
                    {
                        "name": "project",
                        "description": "Initialize a new project workspace folder containing README.md, Tasks.md, and Architecture.md.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Project workspace name"},
                                "company": {"type": "string", "description": "Associated company", "default": "Personal"},
                                "tech": {"type": "string", "description": "Comma-separated tech stack list"},
                                "status": {"type": "string", "description": "Project status (planning, active, paused, done)", "default": "planning"}
                            },
                            "required": ["name"]
                        }
                    }
                ]
            },
            "id": msg_id
        }
        
    elif method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        
        text_result = ""
        is_error = False
        
        try:
            if name == "search":
                query = arguments.get("query")
                tags = arguments.get("tags")
                results, is_semantic = search_vault(vault_path, query, tags)
                search_type = "semantic" if is_semantic else "keyword"
                if not results:
                    text_result = f"No matching notes found (search mode: {search_type})."
                else:
                    lines = [f"Found {len(results)} matching note(s) using {search_type} search:"]
                    for r in results:
                        score_out = f" [score: {r['score']:.2f}]" if is_semantic else ""
                        tags_out = f" [tags: {', '.join(r['tags'])}]" if r['tags'] else ""
                        lines.append(f"- **{r['title']}** (Path: `{r['path']}`){score_out}{tags_out}")
                        if r['excerpt']:
                            lines.append(f"  {r['excerpt']}")
                    text_result = "\n".join(lines)
                    
            elif name == "view":
                note = arguments.get("note")
                section = arguments.get("section")
                text_result = view_note(vault_path, note, section)
                if text_result.startswith("Error:"):
                    is_error = True
                    
            elif name == "links":
                note = arguments.get("note")
                out, inc, resolved_name = find_links(vault_path, note)
                if out is None:
                    text_result = f"Error: Note '{note}' not found."
                    is_error = True
                else:
                    lines = [
                        f"Note: **{resolved_name}**",
                        "\n--- Outgoing Links ---"
                    ]
                    if not out:
                        lines.append("None")
                    for link in out:
                        lines.append(f"- [[{link}]]")
                    lines.append("\n--- Backlinks (Incoming) ---")
                    if not inc:
                        lines.append("None")
                    for link in inc:
                        lines.append(f"- [[{link}]]")
                    text_result = "\n".join(lines)
                    
            elif name == "memo":
                conv_id = arguments.get("conv_id")
                title = arguments.get("title")
                content = arguments.get("content")
                links = arguments.get("links")
                text_result = create_memo(vault_path, conv_id, title, content, links)
                
            elif name == "idea":
                title = arguments.get("title")
                company = arguments.get("company", "Personal")
                problem = arguments.get("problem", "")
                concept = arguments.get("concept", "")
                text_result = create_project(vault_path, title, company, status="incubating", problem=problem, concept=concept)
                
            elif name == "project":
                project_name = arguments.get("name")
                company = arguments.get("company", "Personal")
                tech = arguments.get("tech", "")
                status = arguments.get("status", "planning")
                text_result = create_project(vault_path, project_name, company, tech, status)
                
            else:
                text_result = f"Error: Unknown tool '{name}'"
                is_error = True
                
        except Exception as e:
            text_result = f"Error executing tool '{name}': {e}"
            is_error = True
            
        return {
            "jsonrpc": "2.0",
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": text_result
                    }
                ],
                "isError": is_error
            },
            "id": msg_id
        }
        
    else:
        # Method not found or non-error notification
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            },
            "id": msg_id
        }

def detect_obsidian_vaults():
    vaults = []
    home = os.path.expanduser("~")
    
    # 1. Check obsidian.json configuration file
    paths_to_check = []
    if sys.platform == "darwin":
        paths_to_check.append(os.path.join(home, "Library", "Application Support", "obsidian", "obsidian.json"))
    elif sys.platform.startswith("linux"):
        paths_to_check.append(os.path.join(home, ".config", "obsidian", "obsidian.json"))
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths_to_check.append(os.path.join(appdata, "obsidian", "obsidian.json"))
            
    for p in paths_to_check:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                vaults_dict = data.get("vaults", {})
                for k, v in vaults_dict.items():
                    v_path = v.get("path")
                    if v_path and os.path.exists(v_path):
                        vaults.append(os.path.abspath(v_path))
            except Exception:
                pass
                
    # 2. Check macOS iCloud Obsidian folder specifically
    if sys.platform == "darwin":
        icloud_dir = os.path.join(home, "Library", "Mobile Documents", "iCloud~md~obsidian", "Documents")
        if os.path.exists(icloud_dir):
            try:
                for item in os.listdir(icloud_dir):
                    item_path = os.path.join(icloud_dir, item)
                    if os.path.isdir(item_path):
                        abs_item = os.path.abspath(item_path)
                        if abs_item not in vaults:
                            vaults.append(abs_item)
            except Exception:
                pass
                
    # Filter out duplicates while preserving order
    unique_vaults = []
    for v in vaults:
        if v not in unique_vaults:
            unique_vaults.append(v)
    return unique_vaults

# --- Main Driver ---

def main():
    parser = argparse.ArgumentParser(description="Synapse: AI-Agent Memory Vault CLI Helper")
    parser.add_argument("--vault", help="Path to the Synapse Memory Vault")
    
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")
    
    # Init Subcommand
    subparsers.add_parser("init", help="Initialize Synapse vault folders and templates")
    
    # MCP Subcommand
    subparsers.add_parser("mcp", help="Run the Model Context Protocol (MCP) stdio server")
    
    # Search Subcommand
    s_parser = subparsers.add_parser("search", help="Search vault notes using semantic search")
    s_parser.add_argument("query", nargs="?", help="Search term/phrase")
    s_parser.add_argument("--tags", help="Comma-separated tags to filter by")
    
    # Links Subcommand
    l_parser = subparsers.add_parser("links", help="View note links and backlinks")
    l_parser.add_argument("note", help="Note title or filename")
    
    # View Subcommand
    v_parser = subparsers.add_parser("view", help="View note content or section")
    v_parser.add_argument("note", help="Note title or filename")
    v_parser.add_argument("--section", help="Header section title to print specifically")
    
    # Memo Subcommand
    m_parser = subparsers.add_parser("memo", help="Add agent conversation memory")
    m_parser.add_argument("--conv-id", required=True, help="Conversation ID")
    m_parser.add_argument("--title", required=True, help="Session description")
    m_parser.add_argument("--content", required=True, help="Summary details")
    m_parser.add_argument("--links", help="Comma-separated wiki-links to associate (e.g. 'Projects/App/README')")
    
    # Idea Subcommand (Incubating project)
    i_parser = subparsers.add_parser("idea", help="Create an incubating product idea note")
    i_parser.add_argument("--title", required=True, help="Idea title")
    i_parser.add_argument("--company", default="Personal", help="Company association")
    i_parser.add_argument("--problem", help="Problem statement text")
    i_parser.add_argument("--concept", help="Core concept text")
    
    # Project Subcommand
    p_parser = subparsers.add_parser("project", help="Create an active/planning project workspace")
    p_parser.add_argument("--name", required=True, help="Project name")
    p_parser.add_argument("--company", default="Personal", help="Company association")
    p_parser.add_argument("--tech", help="Comma-separated tech stack list")
    p_parser.add_argument("--status", default="planning", help="Project status (planning, active, paused, done)")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
        
    if args.command == "init":
        vault_path = args.vault or os.environ.get("SYNAPSE_VAULT_PATH") or os.environ.get("OBSIDIAN_VAULT_PATH")
        if not vault_path:
            detected = detect_obsidian_vaults()
            if sys.stdin.isatty():
                print("===============================================")
                print("🔍 Synapse Memory Vault Setup Wizard")
                print("===============================================\n")
                if detected:
                    print("Existing vaults detected on your machine:")
                    for i, d in enumerate(detected, 1):
                        print(f"  [{i}] {d}")
                    print(f"  [{len(detected)+1}] Create a new vault at a custom path")
                    
                    try:
                        choice = input(f"\nSelect a vault choice [1-{len(detected)+1}]: ").strip()
                        if choice.isdigit():
                            choice_idx = int(choice) - 1
                            if 0 <= choice_idx < len(detected):
                                vault_path = detected[choice_idx]
                    except (KeyboardInterrupt, EOFError):
                        print("\nAborted.")
                        sys.exit(1)
                else:
                    print("No existing vaults were automatically detected on your machine.")
                
                if not vault_path:
                    default_new = os.path.expanduser("~/SynapseVault")
                    try:
                        custom = input(f"Enter the absolute path for your vault [{default_new}]: ").strip()
                        vault_path = custom if custom else default_new
                    except (KeyboardInterrupt, EOFError):
                        print("\nAborted.")
                        sys.exit(1)
            else:
                # Non-interactive fallback
                vault_path = DEFAULT_VAULT_PATH
                
        vault_path = os.path.abspath(os.path.expanduser(vault_path))
        init_vault(vault_path)
        if sys.stdin.isatty():
            setup_mcp_config_wizard(vault_path)
    else:
        vault_path = get_vault_path(args)
        if not os.path.exists(vault_path):
            print(f"Error: Vault path '{vault_path}' does not exist. Please run 'init' or specify --vault.")
            sys.exit(1)
            
        if args.command == "mcp":
            run_mcp_server(vault_path)
            
        elif args.command == "search":
            results, is_semantic = search_vault(vault_path, args.query, args.tags)
            search_type = "semantic" if is_semantic else "keyword"
            if not results:
                print(f"No matching notes found (search mode: {search_type}).")
            else:
                print(f"Found {len(results)} matching note(s) using {search_type} search:")
                for r in results:
                    score_out = f" [score: {r['score']:.2f}]" if is_semantic else ""
                    tags_out = f" [tags: {', '.join(r['tags'])}]" if r['tags'] else ""
                    print(f"- **{r['title']}** (Path: `{r['path']}`){score_out}{tags_out}")
                    if r['excerpt']:
                        print(f"  {r['excerpt']}")
                        
        elif args.command == "links":
            out, inc, resolved_name = find_links(vault_path, args.note)
            if out is None:
                print(f"Error: Note '{args.note}' not found.")
            else:
                print(f"Note: **{resolved_name}**")
                print("\n--- Outgoing Links ---")
                if not out:
                    print("None")
                for link in out:
                    print(f"- [[{link}]]")
                print("\n--- Backlinks (Incoming) ---")
                if not inc:
                    print("None")
                for link in inc:
                    print(f"- [[{link}]]")
                    
        elif args.command == "view":
            content = view_note(vault_path, args.note, args.section)
            print(content)
            
        elif args.command == "memo":
            msg = create_memo(vault_path, args.conv_id, args.title, args.content, args.links)
            print(msg)
            
        elif args.command == "idea":
            msg = create_project(vault_path, args.title, args.company, status="incubating", problem=args.problem, concept=args.concept)
            print(msg)
            
        elif args.command == "project":
            msg = create_project(vault_path, args.name, args.company, args.tech, args.status)
            print(msg)

if __name__ == "__main__":
    main()
