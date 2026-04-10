import os
import re
from pathlib import Path
from datetime import datetime

def get_vault_map(vault_root: str) -> str:
    """Generate a text-based tree map of the vault for the LLM context."""
    vault_path = Path(vault_root)
    lines = ["VAULT ROOT: /"]
    relevant_dirs = ["Atomic Notes"]
    
    for d_name in relevant_dirs:
        dir_path = vault_path / d_name
        if not dir_path.exists(): continue
        lines.append(f"/{d_name}")
        for domain in sorted(dir_path.iterdir()):
            if domain.is_dir() and not domain.name.startswith("."):
                lines.append(f"  /{domain.name}")
                for note in sorted(domain.iterdir()):
                    if note.is_file() and note.suffix == ".md":
                        lines.append(f"    - {note.name}")
    return "\n".join(lines)

def save_note_at_path(vault_root: str, relative_path: str, content: str) -> str:
    """Save content to the exact path specified by the LLM (The Architect)."""
    rel_path = relative_path.lstrip("/")
    abs_path = Path(vault_root) / rel_path
    
    # Safety: Ensure it stays within Atomic Notes if path is malformed
    if "Atomic Notes" not in str(abs_path):
        abs_path = Path(vault_root) / "Atomic Notes" / "Misc" / abs_path.name

    # If the file already exists, we might need to handle a title change in the DB
    # We will let the Agent handle the DB update, but we return the path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return str(abs_path.absolute())

def delete_note_by_title(vault_root: str, title: str):
    """Remove a note from the filesystem by its title (Search-based)."""
    vault_path = Path(vault_root) / "Atomic Notes"
    for domain in vault_path.iterdir():
        if not domain.is_dir(): continue
        for note in domain.iterdir():
            if note.suffix == ".md":
                content = note.read_text(encoding="utf-8")
                if f"# {title}" in content or f"title: {title}" in content:
                    note.unlink()
                    return True
    return False

def find_metadata(raw_md: str) -> dict:
    """Extract Title and Domain from Note Markdown for internal indexing."""
    data = {"title": "Untitled", "domain": "Misc"}
    
    # Try parsing frontmatter first (YAML-ish)
    fm_match = re.search(r"^---\s*\n(.*?)\n---", raw_md, re.DOTALL | re.MULTILINE)
    if fm_match:
        fm_content = fm_match.group(1)
        t_match = re.search(r"^title:\s*(.+)$", fm_content, re.MULTILINE | re.IGNORECASE)
        d_match = re.search(r"^domain:\s*(.+)$", fm_content, re.MULTILINE | re.IGNORECASE)
        if t_match: data["title"] = t_match.group(1).strip().strip("'\"")
        if d_match: data["domain"] = d_match.group(1).strip().strip("'\"")

    # Fallback to # Title if not in frontmatter
    if data["title"] == "Untitled":
        title_match = re.search(r"^#\s+(.+)$", raw_md, re.MULTILINE)
        if title_match:
            data["title"] = title_match.group(1).strip()
            
    return data

def update_index(vault_root: str, title: str):
    """Append the note title to the central index.md if not already present."""
    index_path = Path(vault_root) / "index.md"
    entry = f"- [[{title}]]"
    
    content = ""
    if index_path.exists():
        content = index_path.read_text(encoding="utf-8")
        
    if entry not in content:
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(entry + "\n")

def append_log(vault_root: str, action: str, target: str):
    """Append chronological activity to Logs/log.md."""
    log_path = Path(vault_root) / "Logs" / "log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {action} | {target}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)

def read_raw_file(vault_root: str, filename: str) -> str:
    """Read source file from /Raw directory."""
    raw_path = Path(vault_root) / "Raw" / filename
    if not raw_path.exists():
        raise FileNotFoundError(f"Source file {filename} not found in /Raw.")
    return raw_path.read_text(encoding="utf-8")

def list_raw_files(vault_root: str) -> list:
    """List all available files in /Raw for batch ingestion."""
    raw_dir = Path(vault_root) / "Raw"
    if not raw_dir.exists(): return []
    return [f.name for f in raw_dir.iterdir() if f.is_file() and not f.name.startswith(".")]

def archive_raw_file(vault_root: str, filename: str):
    """Move processed file to /Raw/Archive with timestamp if collision occurs."""
    raw_path = Path(vault_root) / "Raw" / filename
    archive_dir = Path(vault_root) / "Raw" / "Archive"
    archive_dir.mkdir(exist_ok=True)
    if raw_path.exists():
        target_path = archive_dir / filename
        if target_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            target_path = archive_dir / f"{timestamp}_{filename}"
        os.rename(raw_path, target_path)
