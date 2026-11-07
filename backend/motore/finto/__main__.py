"""python -m motore.finto — avvia il finto motore.

Host e porta da MOTORE_FINTO_HOST (default 0.0.0.0, adatto a un container Docker)
e MOTORE_FINTO_PORTA (default 8080). Fuori da Docker: MOTORE_FINTO_HOST=127.0.0.1.
"""
import os

import uvicorn

uvicorn.run("motore.finto.app:app", host=os.environ.get("MOTORE_FINTO_HOST", "0.0.0.0"),
            port=int(os.environ.get("MOTORE_FINTO_PORTA", "8080")))
