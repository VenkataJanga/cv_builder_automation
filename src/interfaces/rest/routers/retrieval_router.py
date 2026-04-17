from fastapi import APIRouter, Depends, Query

from src.application.services.retrieval_service import RetrievalService
from src.interfaces.rest.dependencies.auth_dependencies import get_current_user

router = APIRouter(prefix="/retrieval", tags=["retrieval"], dependencies=[Depends(get_current_user)])

retrieval_service = RetrievalService()


@router.get("/context")
def get_context(query: str = Query(..., min_length=2), top_k: int = 3):
    return {
        "query": query,
        "top_k": top_k,
        "results": retrieval_service.get_context(query, top_k=top_k),
    }
