---
name: synapse
description: Search, view, link, and update memories/projects inside a Synapse project memory vault.
---

# Synapse Agent Memory Skill

This skill equips visiting AI agents with the ability to query, navigate, and log persistent memories inside the local Synapse Memory Vault.

## Tools & Commands

Run these commands in the terminal relative to the vault root:

### 1. Search notes semantically
```bash
python3 Tools/synapse.py search "<query>"
```
Use this to locate related notes and past conversation summaries.

### 2. View note sections (Token Optimizer)
```bash
python3 Tools/synapse.py view "<note_path>" --section "<section_header>"
```
Always use this instead of viewing the whole file if you only need a specific section (e.g. database schema, tasks list).

### 3. Log session memories
```bash
python3 Tools/synapse.py memo --conv-id "<conversation_id>" --title "<Title>" --content "<Details>" --links "<Related Notes>"
```
Run this at the end of your session to document what was changed.

### 4. Create projects and ideas
- Product Ideas: `python3 Tools/synapse.py idea --title "<title>" --problem "<problem>" --concept "<concept>"`
- Workspaces: `python3 Tools/synapse.py project --name "<name>" --tech "<tech_stack>" --status "active"`

### 5. Find connections
```bash
python3 Tools/synapse.py links "<note_name>"
```
Lists outgoing wiki-links and incoming backlinks.

## Behavior Guidelines
1. **Never read the whole vault directory structure** or grep blindly. Use the `search` subcommand first.
2. **Always link memories** to relevant project directories.
3. **Log conversation memory** at the end of every task execution.
