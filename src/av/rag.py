import lancedb
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

class RagManager:
    """Handles vector database operations (LanceDB) for the vault."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = lancedb.connect(db_path)
        self.table_name = "notes"
        
    def _get_table(self) -> Optional[lancedb.table.Table]:
        """Return the notes table if it exists."""
        if self.table_name in self.db.table_names():
            return self.db.open_table(self.table_name)
        return None

    def upsert_note(self, title: str, domain: str, content: str, vector: List[float], file_path: str):
        """Mirror note content into the vector database using file_path as unique ID."""
        table = self._get_table()
        
        record = {
            "title": title,
            "domain": domain,
            "content": content,
            "vector": vector,
            "file_path": file_path,
            "updated": datetime.now().isoformat()
        }
        df = pd.DataFrame([record])
        
        if table:
            # Atomic update via delete-then-add based on file_path (Unique ID)
            table.delete(f'file_path = "{file_path}"')
            table.add(df)
        else:
            self.db.create_table(self.table_name, data=df)

    def delete_note_by_path(self, file_path: str):
        """Remove a note from the vector DB by its absolute or relative path."""
        table = self._get_table()
        if table:
            table.delete(f'file_path = "{file_path}"')

    def search_similar(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Perform semantic search for similar technical notes."""
        table = self._get_table()
        if not table:
            return []
        return table.search(query_vector).limit(limit).to_list()

    def get_vault_stats(self) -> Dict[str, Any]:
        """Aggregate vault statistics for health reports."""
        table = self._get_table()
        if not table:
            return {"total_notes": 0, "by_domain": {}}
            
        df = table.to_pandas()
        return {
            "total_notes": len(df),
            "by_domain": df['domain'].value_counts().to_dict() if 'domain' in df.columns else {}
        }

    def get_all_notes_metadata(self) -> List[Dict[str, Any]]:
        """Fetch lightweight summary of every note for auditing."""
        table = self._get_table()
        if not table:
            return []
        
        # We only pull columns needed for linting to save memory/tokens
        df = table.to_pandas()
        if df.empty:
            return []
        
        # Calculate length and extract basic info
        df['content_length'] = df['content'].str.len()
        # Remove full content and vector for the metadata list
        metadata_cols = ['title', 'domain', 'updated', 'content_length']
        return df[metadata_cols].to_dict(orient='records')
