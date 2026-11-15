"""Entry point so the server can be started with ``python -m cricbuzz_api.server``."""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "cricbuzz_api.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "12000")),
        reload=False,
    )
