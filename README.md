# ⚛️ Atomic-Vault
### *LLM-as-Architect: The Autonomous Technical Knowledge Engine*

Atomic-Vault is not just a note-taking app; it's a **self-organizing knowledge engine**. It uses a Large Language Model (LLM) as an "Architect" to manage a library of atomic technical notes, ensuring they are structured, linked, and searchable.

---

## 🧠 How It Works: The Architect Pattern

Atomic-Vault operates on a **Decoupled Architecture** where the LLM makes decisions (The Architect) and the Python CLI executes them (The Executor).

### 1. The Ingestion Pipeline
When you drop a raw file into `/Raw` and run `av ingest`:
1. **Semantic Context**: The system generates a vector embedding of your raw input using `fastembed`.
2. **Memory Retrieval**: It queries `LanceDB` for the top 5 most similar existing notes to provide the LLM with context.
3. **Architectural Decision**: The LLM receives the raw content + existing context + the `AGENT.md` protocol. It then decides:
   - Should this be a new note?
   - Should it update an existing one?
   - Which **Domain** (e.g., AWS, Security) does it belong to?
4. **Execution**: The CLI parses the LLM's `FILE:` and `CONTENT:` blocks, writes the Markdown files, updates the central `index.md`, and syncs the vector database.

### 2. The Semantic Layer
Every note is automatically indexed into a local **LanceDB** instance.
- **Embeddings**: Powered by `fastembed` (defaulting to the highly efficient `BAAI/bge-small-en-v1.5` model).
- **Search**: When you "lint" or "sync", the system uses vector similarity to find redundancies or missing links between domains.

### 3. The Master Protocol (`AGENT.md`)
The behavior of your vault is governed by `AGENT.md`. This file tells the LLM:
- **Naming Conventions**: Title Case for files.
- **Atomicity**: One technical concept per note.
- **Linking Logic**: How to connect related concepts.

---

## 🚀 Key Features

- **🤖 Autonomous Organization**: No manual filing. The LLM decides the folder structure.
- **⚡ High Performance**: `LanceDB` and `fastembed` provide sub-millisecond search without a GPU.
- **🛠️ Self-Healing (Linting)**: Run `av lint --fix` to let the Architect find technical gaps or redundant information and automatically merge or update notes.
- **📁 Transparent Storage**: Your knowledge is stored in plain Markdown with YAML frontmatter. No proprietary formats.

---

## 🛠️ Installation

### Prerequisites
- **Python 3.10+**
- **C Compiler** (`gcc`/`g++`) for vector extensions.

```bash
git clone https://github.com/Lordsofzzzz/Atomic-Vault.git
cd Atomic-Vault
pip install -e .
```

---

## 📖 CLI Commands

| Command | Action |
| :--- | :--- |
| `av init` | Scaffolds the vault, sets up `/Raw`, `/Atomic Notes`, and configures the LLM provider. |
| `av ingest` | Processes everything in the `/Raw` folder into atomic notes. |
| `av sync` | Rebuilds the entire Vector DB from the Markdown files (useful if you edit files manually). |
| `av lint` | Audits the vault for density gaps, redundancy, and critical link failures. |
| `av status` | Shows vault metrics (total notes, distribution by domain). |

---

## 📂 Vault Structure

```text
/your-vault-root
├── AGENT.md           # The Master Protocol (System Prompt)
├── index.md           # Chronological and Domain-based index
├── .av-db/            # LanceDB vector storage
├── Raw/               # Where you drop new information
│   └── Archive/       # Processed source files
└── Atomic Notes/      # The structured vault
    ├── AWS/
    ├── Security/
    └── ...
```

---

## 📜 Tech Stack

- **Orchestration**: `litellm` (OpenAI, Anthropic, Ollama, etc.)
- **Vector DB**: `lancedb`
- **Embeddings**: `fastembed`
- **UI**: `rich` & `click`

---

Developed by **Aditya** | [GitHub Repo](https://github.com/Lordsofzzzz/Atomic-Vault)
