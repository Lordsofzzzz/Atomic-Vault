import re
import json
from pathlib import Path
from typing import List, Optional, Iterable
import litellm
from pydantic import BaseModel, Field, field_validator
from fastembed import TextEmbedding
from .rag import RagManager
from . import tools

class NoteAction(BaseModel):
    """Represents a single file operation directed by the Architect."""
    file_path: str = Field(..., description="The relative path to the file (e.g., 'Atomic Notes/AWS/Lambda.md' or 'index.md')")
    content: str = Field(..., description="The full markdown content of the file")
    is_deletion: bool = Field(default=False, description="Whether this file should be deleted")

class ArchitectResponse(BaseModel):
    """The structured response from the Architect containing multiple actions."""
    summary: str = Field(..., description="A brief summary of the changes made")
    actions: List[NoteAction] = Field(
        ..., 
        description="A list of NoteAction objects. IMPORTANT: Each item in this list MUST be a full object with 'file_path', 'content', and 'is_deletion'. DO NOT return a count or a list of numbers. You MUST return the actual text content for every file you want to create or update."
    )

class Agent:
    """Orchestrator for the Atomic Vault knowledge engine."""

    def __init__(self, config: dict):
        self.config = config
        self.vault_root = config["vault_root"]
        self.db_path = str(Path(self.vault_root) / ".av-db")
        self.rag = RagManager(self.db_path)
        self.model = f"{config['provider']}/{config['model']}"
        self.embedding_model = TextEmbedding()

    def _get_agent_md(self) -> str:
        """Fetch the Master Protocol (AGENT.md) from the vault root."""
        agent_path = Path(self.vault_root) / "AGENT.md"
        if not agent_path.exists():
            agent_path = Path(__file__).parent.parent / "AGENT.md"
        return agent_path.read_text(encoding="utf-8")

    def _embed(self, text: str) -> list:
        """Generate vector for memory indexing using FastEmbed."""
        embeddings = list(self.embedding_model.embed([text]))
        return embeddings[0].tolist()

    # Tool functions that the LLM can call
    def read_note(self, file_path: str) -> str:
        """Read the full content of an existing note."""
        abs_path = Path(self.vault_root) / file_path.lstrip("/")
        if abs_path.exists() and abs_path.is_file():
            return abs_path.read_text(encoding="utf-8")
        return f"Error: File {file_path} not found."

    def list_vault(self, directory: str = "Atomic Notes") -> str:
        """List files and subdirectories in the vault."""
        return tools.get_vault_map(self.vault_root)

    def ingest(self, filename: str) -> int:
        """Directs the LLM Architect to process raw input and place notes."""
        raw_content = tools.read_raw_file(self.vault_root, filename)
        vault_map = tools.get_vault_map(self.vault_root)
        agent_protocol = self._get_agent_md()
        
        # Get current index for context
        index_path = Path(self.vault_root) / "index.md"
        current_index = index_path.read_text(encoding="utf-8") if index_path.exists() else "No index yet."
        
        query_vector = self._embed(raw_content[:500])
        similar_notes = self.rag.search_similar(query_vector, limit=5)
        
        context_str = f"CURRENT VAULT MAP (Directory Structure):\n{vault_map}\n\nCURRENT INDEX:\n{current_index}\n\n### Similar Notes from Memory:\n\n"
        for note in similar_notes:
            context_str += f"--- {note['title']} ---\n{note['content']}\n\n"

        schema_json = json.dumps(ArchitectResponse.model_json_schema(), indent=2)

        user_prompt = f"""PROCESS FILE: {filename}
CONTENT:
{raw_content}

{context_str}

TASK: Segment the content into atomic technical notes.
You MUST return a JSON object that matches this schema:
{schema_json}
"""

        # Using raw litellm with JSON mode to bypass instructor validation issues with some providers
        completion = litellm.completion(
            model=self.model,
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": agent_protocol},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        raw_response = completion.choices[0].message.content
        # print(f"DEBUG RAW RESPONSE: {raw_response}") # Useful for debugging
        try:
            response_data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            # Try to extract JSON if there is preamble
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group(0))
            else:
                raise e
        
        response = ArchitectResponse.model_validate(response_data)


        return self._execute_actions(response)

    def _execute_actions(self, response: ArchitectResponse) -> int:
        """Executes the file operations defined in the structured Architect response."""
        total_ops = 0
        
        for action in response.actions:
            total_ops += self._execute_single_action(action)
                
        return total_ops

    def _execute_single_action(self, action: NoteAction) -> int:
        """Executes a single file operation."""
        target_path = action.file_path.strip()
        
        if action.is_deletion:
            try:
                abs_path = Path(self.vault_root) / target_path.lstrip("/")
                if abs_path.exists() and abs_path.is_file():
                    abs_path.unlink()
                    self.rag.delete_note_by_path(target_path)
                    return 1
            except Exception as e:
                print(f"Deletion failed: {e}")
            return 0

        # Handle creations and updates
        try:
            markdown_content = action.content.strip()
            if len(markdown_content) < 50 and target_path.lower() != "index.md":
                return 0
            
            is_index = target_path.lower() == "index.md"
            actual_path = tools.save_note_at_path(self.vault_root, target_path, markdown_content)
            meta = tools.find_metadata(markdown_content)
            
            if not is_index:
                tools.append_log(self.vault_root, "architect", target_path)
                vector = self._embed(markdown_content[:2000])
                self.rag.upsert_note(meta["title"], meta["domain"], markdown_content, vector, target_path)
                return 1
            return 0
        except Exception as e:
            print(f"Architect action failed: {e}")
            return 0

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
        
        fix_instruction = "LINT MODE: Identify gaps, redundancies, and link failures."
        if fix:
            fix_instruction += " FIX MODE ENABLED: Remediate issues by issuing NoteActions."

        schema_json = json.dumps(ArchitectResponse.model_json_schema(), indent=2)

        user_prompt = f"""{audit_context}

PERFORM VAULT LINT according to Section 3 of your protocol.
{fix_instruction}

You MUST return a JSON object that matches this schema:
{schema_json}
"""

        completion = litellm.completion(
            model=self.model,
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": protocol},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        raw_response = completion.choices[0].message.content
        try:
            response_data = json.loads(raw_response)
        except json.JSONDecodeError as e:
            # Try to extract JSON if there is preamble
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group(0))
            else:
                raise e
        
        response = ArchitectResponse.model_validate(response_data)
        
        if fix:
            self._execute_actions(response)
            
        return {
            "summary": response.summary,
            "actions": [a.model_dump() for a in response.actions],
            "raw": response.model_dump_json(indent=2)
        }

