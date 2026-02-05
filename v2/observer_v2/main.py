from __future__ import annotations

import uvicorn


def run() -> None:
    uvicorn.run("observer_v2.app:app", host="0.0.0.0", port=8080, reload=False)


if __name__ == "__main__":
    run()
