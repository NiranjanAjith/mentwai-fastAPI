from app.framework.tools import Tool
from typing import Dict, Any, List
from datetime import datetime

from pinecone import Pinecone

from app.core.logging import get_logger
logger = get_logger(__name__)

from app.core.config import settings



class VectorTool(Tool):
    name: str
    is_ready: bool = False

    async def confirm_setup(self) -> bool:
        raise NotImplementedError

    async def upsert(self) -> None:
        raise NotImplementedError

    async def query(self) -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def delete(self) -> None:
        raise NotImplementedError




class PineconeProvider(VectorTool):
    def __init__(self):
        
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)

        index_name = "textbook"
        if index_name not in pc.list_indexes().names():
            pc.create_index(
                name=index_name,
                dimension=1024,
                metric="cosine"
            )
        self.index = pc.Index(index_name)
        self.inference = pc.inference

    def confirm_setup(self):
        if self.index and self.inference:
            logger.info(f"[VectorDB] Pinecone index '{self.index.name}' is ready.")
            return True
        else:
            logger.error("[VectorDB] Pinecone index or inference client not initialized.")
            return False

    async def run(self, query: str, namespace:str, filters: dict= {}, top_k: int = 3):
        try:
            self.pinecone_namespace = namespace
            results = await self.query(query, filters, top_k)
            return results
        except Exception as e:
            return f"[VectorDB Error] {str(e)}"

    async def query(self, query: str, filters: dict, top_k: int = 3) -> list[Dict]:
        if not self.index:
            raise RuntimeError("Pinecone index not initialized.")

        logger.info(f"Start Vector Store Search: {datetime.now().time()}")
        embedding = self._embed_query(query)
        filter_conditions = self._build_filters(filters)

        logger.info("\t=+=+=Pinecone Logs=+=+=")
        logger.info(f"Metadata filters:\n{filter_conditions}\n")

        try:
            results = self.index.query(
                namespace=self.pinecone_namespace,
                vector=embedding,
                filter=filter_conditions,
                top_k=top_k,
                include_values=False,
                include_metadata=True
            )
        except Exception as e:
            logger.error(f"Pinecone Querying Error: {e}")
            raise

        logger.info(f"Vector Store Response Received: {datetime.now().time()}")

        if not results or not results['matches']:
            logger.warning("No matching documents found in index")
            return ["No matches found in the textbook. Reply with a brief surface level explanation."]

        return self._format_results(results['matches'])

    def _embed_query(self, query: str) -> list[float]:
        try:
            embedding = self.inference.embed(
                model="multilingual-e5-large",
                inputs=[query],
                parameters={"input_type": "query"}
            )
            return embedding[0].values
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}")

    def _build_filters(self, filters: dict) -> dict:
        for key, value in filters.items():
            if key in ['text', 'source_file', 'processed_at']:
                continue
            if isinstance(value, str):
                filters[key] = value.replace(",", " ").replace(" ", "-").lower()

        return {
            "$or": [
                {key: {"$in": value}} for key, value in filters.items() if isinstance(value, list)
            ] + [
                {key: {"$eq": value}} for key, value in filters.items() if not isinstance(value, list)
            ]
        }

    def _format_results(self, matches: list[dict]) -> list[Dict]:
        formatted = []
        for match in matches:
            distance = match.get('score', 1.0)
            metadata = match.get('metadata', {}).copy()
            relevance = round(1 - distance, 4)
            text = metadata.get('text', '')

            formatted.append({
                "relevance": relevance,
                "text": text,
                "metadata": metadata
            })
        logger.info(f"CONTEXT:\n{formatted}")
        return formatted




vector_db = PineconeProvider()