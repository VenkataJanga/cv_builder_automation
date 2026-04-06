from fastapi import APIRouter, Query

from src.application.services.retrieval_service import RetrievalService

router = APIRouter(prefix="/retrieval", tags=["retrieval"])

retrieval_service = RetrievalService()


@router.get("/context")
def get_context(query: str = Query(..., min_length=2), top_k: int = 3):
    return {
        "query": query,
        "top_k": top_k,
        "results": retrieval_service.get_context(query, top_k=top_k),
    }
