import uvicorn

from . import *

port = int(os.getenv("BACKEND_PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
