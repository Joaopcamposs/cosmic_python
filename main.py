from fastapi import FastAPI, HTTPException, status
from datetime import datetime
from allocation.domain import commands
from allocation.service_layer.handlers import InvalidSku
from allocation import bootstrap, views

app = FastAPI()
bus = bootstrap.bootstrap()


@app.post("/add_batch", status_code=status.HTTP_201_CREATED)
def add_batch(ref: str, sku: str, qty: int, eta: str = None):
    eta_date = datetime.fromisoformat(eta).date() if eta else None
    cmd = commands.CreateBatch(ref, sku, qty, eta_date)
    bus.handle(cmd)
    return {"message": "OK"}


@app.post("/allocate", status_code=status.HTTP_202_ACCEPTED)
def allocate(orderid: str, sku: str, qty: int):
    try:
        cmd = commands.Allocate(orderid, sku, qty)
        bus.handle(cmd)
    except InvalidSku as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "OK"}


@app.get("/allocations/{orderid}")
def allocations_view(orderid: str):
    result = views.allocations(orderid, bus.uow)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=80)
