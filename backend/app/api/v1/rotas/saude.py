from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.banco import obter_sessao

router = APIRouter(tags=["Saúde"])


class Saude(BaseModel):
    status: Literal["ok", "degradado"]
    banco: Literal["ok", "indisponivel"]


@router.get("/health", response_model=Saude, summary="Verifica a API e o banco")
def verificar_saude(response: Response, sessao: Annotated[Session, Depends(obter_sessao)]) -> Saude:
    try:
        sessao.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return Saude(status="degradado", banco="indisponivel")
    return Saude(status="ok", banco="ok")
