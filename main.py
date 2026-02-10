"""Ponto de entrada principal para executar a aplicação localmente."""

import uvicorn

from allocation.entrypoints.fastapi_app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
