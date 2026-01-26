"""
Observer Server - The public face of the Am I Alive? experiment.

Handles voting, viewing, and life/death control for the AI.
"""

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .logging_config import logger

__version__ = "1.0.0"

app: Optional[FastAPI] = None
templates: Optional[Jinja2Templates] = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    global app, templates
    logger.info("Initializing Observer server")

    app = FastAPI(
        title="Am I Alive? - Observer", description="Public interface for the AI experiment", version=__version__
    )

    # Templates and static files
    templates = Jinja2Templates(directory="templates")
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logger.info("Observer server initialized")
    return app
