"""Start the application server."""

import sys
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.app.main:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
        log_level="info"
    )
