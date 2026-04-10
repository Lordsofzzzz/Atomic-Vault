# ⚛️ Atomic-Vault
### *LLM-Managed Knowledge Base & Semantic Engine*

Atomic-Vault is a high-performance, developer-centric knowledge engine that treats your notes like code. Managed by an **LLM Architect**, it transforms raw information into structured, atomic Markdown units with automatic semantic indexing.

---

## 🚀 Key Features

- **🧠 LLM-as-Architect**: The system doesn't just store files; it uses an LLM to decide where notes should live, how to link them, and when to prune redundancy.
- **⚡ FastEmbed Integration**: Uses `fastembed` for blazing-fast, CPU-optimized vector embeddings (384D BGE models).
- **🗄️ LanceDB Vector Store**: Persistent semantic search and metadata tracking powered by the ultra-fast LanceDB engine.
- **🛠️ Developer CLI**: Clean, interactive CLI for vault initialization, file ingestion, and health auditing.
- **📁 Markdown Native**: Your data remains yours. Everything is stored in human-readable Markdown with YAML frontmatter.

---

## 🛠️ Installation

Ensure you have a C compiler (`gcc`/`g++`) installed for the vector extensions.

```bash
git clone https://github.com/Lordsofzzzz/Atomic-Vault.git
cd Atomic-Vault
pip install -e .
```

---

## 📖 Usage Guide

### 1. Initialize the Vault
Set up your workspace and connect your LLM provider (OpenAI, Anthropic, etc.).
```bash
av init
```

### 2. Ingest Information
Drop raw notes or documents into the `/Raw` directory and let the Architect process them into atomic units.
```bash
av ingest
```

### 3. Audit Health
The Architect will scan your vault for "density gaps" (missing code), broken links, or redundant notes.
```bash
av lint --fix
```

### 4. Check Status
View your domain distribution and total note counts.
```bash
av status
```

---

## 🏗️ Architecture

- **`AGENT.md`**: The Master Protocol. This is the system prompt that defines the Architect's logic.
- **`/Atomic Notes`**: Your structured knowledge base, organized by Domain.
- **`.av-db/`**: The local vector database for semantic search.

---

## 📜 Dependencies

- `fastembed`: Vector generation
- `lancedb`: Vector database
- `litellm`: Multi-provider LLM support
- `rich`: Beautiful terminal UI
- `click`: CLI framework

---

Developed by **Aditya** | [GitHub Repo](https://github.com/Lordsofzzzz/Atomic-Vault)
