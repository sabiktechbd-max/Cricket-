"""Entry point so the server can be started with ``python -m cricbuzz_api.server``."""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("cricbuzz_api.main:app", host="0.0.0.0", port=8000, reload=False)
