import re
from pathlib import Path
import litellm
from .rag import RagManager
from . import tools

class Agent:
    """Orchestrator for the Atomic Vault knowledge engine."""

    def __init__(self, config: dict):
        self.config = config
        self.vault_root = config["vault_root"]
        self.db_path = str(Path(self.vault_root) / ".av-db")
        self.rag = RagManager(self.db_path)
        self.model = f"{config['provider']}/{config['model']}"

    def _get_agent_md(self) -> str:
        """Fetch the Master Protocol (AGENT.md) from the vault root."""
        agent_path = Path(self.vault_root) / "AGENT.md"
        if not agent_path.exists():
            agent_path = Path(__file__).parent.parent / "AGENT.md"
        return agent_path.read_text(encoding="utf-8")

    def _embed(self, text: str) -> list:
        """Generate dummy vector for memory indexing."""
        import random
        return [random.uniform(-1, 1) for _ in range(384)]

    def ingest(self, filename: str) -> int:
        """Directs the LLM Architect to process raw input and place notes."""
        raw_content = tools.read_raw_file(self.vault_root, filename)
        vault_map = tools.get_vault_map(self.vault_root)
        agent_protocol = self._get_agent_md()
        
        query_vector = self._embed(raw_content[:500])
        similar_notes = self.rag.search_similar(query_vector, limit=5)
        
        context_str = f"CURRENT VAULT MAP:\n{vault_map}\n\n### Similar Notes from Memory:\n\n"
        for note in similar_notes:
            context_str += f"--- {note['title']} ---\n{note['content']}\n\n"

        user_prompt = f"""PROCESS FILE: {filename}
CONTENT:
{raw_content}

{context_str}

REMINDER: Start directly with 'FILE: '. Output ONLY the required FILE/CONTENT blocks."""

        response = litellm.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": agent_protocol},
                {"role": "user", "content": user_prompt}
            ]
        )

        raw_output = response.choices[0].message.content
        return self._process_llm_output(raw_output)

    def _process_llm_output(self, raw_output: str) -> int:
        """Parses the Architect's directive and executes file operations."""
        # Handle DELETION directives
        delete_matches = re.findall(r"DELETE:\s*(.+)", raw_output, flags=re.IGNORECASE)
        for target in delete_matches:
            try:
                target_path = target.strip()
                abs_path = Path(self.vault_root) / target_path.lstrip("/")
                if abs_path.exists() and abs_path.is_file():
                    abs_path.unlink()
                    self.rag.delete_note_by_path(target_path)
            except Exception as e:
                print(f"Deletion failed: {e}")

        # Split into FILE blocks
        blocks = re.split(r"FILE:\s*", raw_output, flags=re.IGNORECASE)
        created_count = 0
        
        for block in blocks:
            if "CONTENT:" not in block.upper(): continue
            try:
                parts = re.split(r"CONTENT:\s*", block, 1, flags=re.IGNORECASE)
                target_path = parts[0].strip()
                markdown_content = parts[1].strip()
                
                if len(markdown_content) < 50: continue
                
                # Save and Index
                tools.save_note_at_path(self.vault_root, target_path, markdown_content)
                meta = tools.find_metadata(markdown_content)
                tools.update_index(self.vault_root, meta["title"])
                tools.append_log(self.vault_root, "architect", target_path)
                
                # Vector DB Sync
                vector = self._embed(markdown_content[:2000])
                self.rag.upsert_note(meta["title"], meta["domain"], markdown_content, vector, target_path)
                created_count += 1
            except Exception as e:
                print(f"Architect directive failed: {e}")
                
        return created_count + len(delete_matches)


    def lint(self, fix: bool = False) -> dict:
        """Vector-driven vault health audit with structured output."""
        metadata = self.rag.get_all_notes_metadata()
        vault_map = tools.get_vault_map(self.vault_root)
        raw_files = tools.list_raw_files(self.vault_root)
        
        protocol = self._get_agent_md()
        
        audit_context = f"""
### STATE OF THE VAULT
VAULT MAP:
{vault_map}

UN-INGESTED RAW FILES:
{raw_files}

METADATA FROM VECTOR DB:
{metadata}
"""
        
        fix_instruction = ""
        if fix:
            fix_instruction = "FIX MODE ENABLED: Remediate density, links, and domains. Use [FIX_LOG] tags."

        user_prompt = f"""{audit_context}

PERFORM VAULT LINT according to Section 3 of your protocol.
{fix_instruction}

GUIDELINE: Be PRAGMATIC. Do NOT flag minor naming mismatches between filenames and internal titles (e.g. "AWS - Lambda" vs "AWS: Lambda") as issues. 
Focus ONLY on:
1. Significant Technical Density gaps (missing code/logic).
2. Major Redundancy (exact duplicate notes).
3. Critical Link gaps between related Domains.

IMPORTANT: You MUST use the following exact tags for EVERY finding:
[SUMMARY]: <one line>
[ISSUE: Type | File | Action]
[FIX_LOG: File | Detail] (only in fix mode)

Example:
[SUMMARY]: Found 2 issues.
[ISSUE: Density | api_test.md | Add code examples]

Do NOT use any other headers like [REDUNDANCY_DETECTED]. Use ONLY the [ISSUE:] tag."""

        response = litellm.completion(
            model=self.model,
            messages=[
                {"role": "system", "content": protocol},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        raw_output = response.choices[0].message.content
        
        # Parse tags
        report_data = {
            "summary": "No summary found.",
            "issues": [],
            "fixes": [],
            "raw": raw_output
        }
        
        for line in raw_output.split("\n"):
            line = line.strip()
            if not line: continue
            
            if line.startswith("[SUMMARY]:"):
                report_data["summary"] = line.replace("[SUMMARY]:", "").strip()
            elif line.startswith("[ISSUE:"):
                # Format: [ISSUE: type | file | action]
                content = line[7:-1]
                parts = [p.strip() for p in content.split("|")]
                if len(parts) >= 3:
                    report_data["issues"].append({"type": parts[0], "file": parts[1], "action": parts[2]})
            elif line.startswith("["):
                # Fallback for untagged but bracketed headers like [DOMAIN_INCONSISTENCY]
                tag = line[1:].split("]")[0].replace("_", " ").title()
                # Check next line for file/action
                continue 
            elif line.startswith("- **File") or line.startswith("- **Issue"):
                # Try to extract from the list if we have a current tag
                pass

        # If no issues were parsed but we have text, add a generic issue for the user to see in verbose
        if not report_data["issues"] and "[ISSUE:" not in raw_output:
             if "[" in raw_output:
                 report_data["summary"] = "Architect used non-standard tags. Use --verbose to see full report."


        if fix:
            self._process_llm_output(raw_output)
            
        return report_data
