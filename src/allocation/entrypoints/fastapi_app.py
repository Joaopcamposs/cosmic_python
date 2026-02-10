"""Entrypoint FastAPI para o serviço de alocação."""

from datetime import date, datetime

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

from allocation import bootstrap, views
from allocation.domain import commands
from allocation.service_layer.handlers import InvalidSku

app = FastAPI(
    title="Allocation Service",
    description="Serviço de alocação de estoque - Cosmic Python",
    version="1.0.0",
)
bus = bootstrap.bootstrap()


class AddBatchRequest(BaseModel):
    """Schema de requisição para adicionar um lote."""

    ref: str
    sku: str
    qty: int
    eta: str | None = None


class AllocateRequest(BaseModel):
    """Schema de requisição para alocar um pedido."""

    orderid: str
    sku: str
    qty: int


class MessageResponse(BaseModel):
    """Schema de resposta padrão."""

    message: str


class AllocationItem(BaseModel):
    """Schema de um item de alocação na resposta."""

    sku: str
    batchref: str


@app.post(
    "/add_batch",
    status_code=status.HTTP_201_CREATED,
    response_model=MessageResponse,
)
def add_batch_endpoint(request: AddBatchRequest) -> MessageResponse:
    """Adiciona um novo lote de produtos.

    Args:
        request: Dados do lote a ser criado.

    Returns:
        Mensagem de confirmação.
    """
    eta_date: date | None = None
    if request.eta is not None:
        eta_date = datetime.fromisoformat(request.eta).date()
    cmd = commands.CreateBatch(request.ref, request.sku, request.qty, eta_date)
    bus.handle(cmd)
    return MessageResponse(message="OK")


@app.post(
    "/allocate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=MessageResponse,
)
def allocate_endpoint(request: AllocateRequest) -> MessageResponse:
    """Aloca uma linha de pedido a um lote disponível.

    Args:
        request: Dados da alocação.

    Returns:
        Mensagem de confirmação.

    Raises:
        HTTPException: Se o SKU não existir (400).
    """
    try:
        cmd = commands.Allocate(request.orderid, request.sku, request.qty)
        bus.handle(cmd)
    except InvalidSku as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    return MessageResponse(message="OK")


@app.get(
    "/allocations/{orderid}",
    response_model=list[AllocationItem],
)
def allocations_view_endpoint(orderid: str) -> list[dict[str, str]]:
    """Consulta as alocações de um pedido.

    Args:
        orderid: Identificador do pedido.

    Returns:
        Lista de alocações com sku e batchref.

    Raises:
        HTTPException: Se não houver alocações (404).
    """
    result = views.allocations(orderid, bus.uow)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return result
