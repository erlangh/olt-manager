#!/usr/bin/env python3
"""
Entry point for the OLT Manager backend application.
This file handles the proper module imports and starts the FastAPI application.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Set the working directory to backend
os.chdir(backend_dir)

if __name__ == "__main__":
    import uvicorn
    from main import app
    
    # Start the application
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )