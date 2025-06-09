# rag_pipeline.py

from llama_index.core import Document, VectorStoreIndex
from llama_index.core.settings import Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.ollama import OllamaEmbedding

# This is the "database" that the RAG system will have knowledge of.
MOCK_DATABASE = {
  "123-ABC": {
    "canonical_name": "XPO Logistics, Inc.",
    "aliases": ["XPO Logistics", "RXO Logistics"]
  },
  "456-DEF": {
    "canonical_name": "Global Tech Partners LLC",
    "aliases": ["Global Tech", "GTP"]
  },
  "789-GHI": {
    "canonical_name": "Stellapps",
    "aliases": ["Stellapps Technologies", "Boon AI"]
  }
}

def create_knowledge_base(db: dict) -> list[Document]:
    """Converts the mock database into a list of Document objects for LlamaIndex."""
    knowledge_base = []
    for db_id, data in db.items():
        doc_text = (
            f"Database ID: {db_id}\n"
            f"Company Name: {data['canonical_name']}\n"
            f"Known Aliases: {', '.join(data['aliases'])}"
        )
        knowledge_base.append(Document(text=doc_text))
    return knowledge_base

class SimpleRAG:
    """A simple, reusable class for the RAG pipeline."""
    def __init__(self, llm_model: str, embedding_model: str):
        print("Initializing RAG pipeline...")
        Settings.llm = Ollama(model=llm_model)
        Settings.embed_model = OllamaEmbedding(model_name=embedding_model)

        knowledge_base = create_knowledge_base(MOCK_DATABASE)
        
        print("Creating vector index from knowledge base... (This might take a moment the first time)")
        self.index = VectorStoreIndex.from_documents(knowledge_base)

        print("Creating query engine...")
        self.query_engine = self.index.as_query_engine()
        
        print("RAG Pipeline is ready.")

    def find_vendor_details(self, extracted_vendor_name: str) -> str:
        """Uses RAG to find the canonical vendor details."""
        print(f"RAG: Searching for vendor '{extracted_vendor_name}'...")
        query = f"Provide all details for the company named '{extracted_vendor_name}'. If you find a match, respond with the full text from your knowledge base. If not, respond with 'No match found.'"
        response = self.query_engine.query(query)
        return str(response)