#!/usr/bin/env python3
"""
Startup script for Alabama Auction Watcher Backend API
Initializes database, creates tables, and starts the development server
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Add backend_api to Python path
backend_path = Path(__file__).parent / "backend_api"
sys.path.insert(0, str(backend_path))

async def initialize_database():
    """Initialize database and create tables."""
    try:
        print("[INFO] Initializing database...")

        # Import database components
        from backend_api.database.connection import create_tables, connect_db, disconnect_db
        from backend_api.database.models import initialize_counties

        # Connect to database
        await connect_db()

        # Create tables
        await create_tables()
        print("[SUCCESS] Database tables created")

        # Initialize Alabama counties
        initialize_counties()
        print("[SUCCESS] Alabama counties initialized")

        # Disconnect (will reconnect when server starts)
        await disconnect_db()

        return True

    except Exception as e:
        print(f"[ERROR] Database initialization failed: {str(e)}")
        return False

def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        print("[INFO] Checking dependencies...")

        required_packages = {
            "fastapi": "fastapi",
            "uvicorn": "uvicorn",
            "sqlalchemy": "sqlalchemy",
            "databases": "databases",
            "pydantic": "pydantic",
            "python-jose": "jose",  # Package name vs import name
            "passlib": "passlib",
            "slowapi": "slowapi"
        }

        missing = []
        for package_name, import_name in required_packages.items():
            try:
                __import__(import_name)
            except ImportError:
                missing.append(package_name)

        if missing:
            print(f"[ERROR] Missing packages: {', '.join(missing)}")
            print("[INFO] Install with: pip install -r requirements.txt")
            return False

        print("[SUCCESS] All dependencies available")
        return True

    except Exception as e:
        print(f"[ERROR] Dependency check failed: {str(e)}")
        return False

def start_server():
    """Start the FastAPI development server."""
    try:
        print("[INFO] Starting FastAPI development server...")

        import uvicorn
        from backend_api.main import app

        # Start server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8001,
            reload=False,
            log_level="info",
            access_log=True
        )

    except KeyboardInterrupt:
        print("\n[INFO] Server stopped by user")
    except Exception as e:
        print(f"[ERROR] Server startup failed: {str(e)}")
        return False

    return True

async def validate_python_scripts():
    """Validate that the required Python algorithms are available."""
    try:
        print("[INFO] Validating Python algorithms...")

        # Test imports
        from scripts.utils import calculate_investment_score, calculate_water_score
        from config.settings import INVESTMENT_SCORE_WEIGHTS

        # Test calculations with known values
        test_investment = calculate_investment_score(5000.0, 3.0, 6.0, 0.8, INVESTMENT_SCORE_WEIGHTS)
        test_water = calculate_water_score("Beautiful creek frontage")

        # Validate results
        if abs(test_investment - 52.8) > 0.5:
            print(f"[WARNING] Investment score algorithm may have changed: expected ~52.8, got {test_investment}")

        if abs(test_water - 3.0) > 0.1:
            print(f"[WARNING] Water score algorithm may have changed: expected 3.0, got {test_water}")

        print("[SUCCESS] Python algorithms validated")
        return True

    except ImportError as e:
        print(f"[ERROR] Python algorithm import failed: {str(e)}")
        print("[INFO] Make sure you're running from the auction root directory")
        return False
    except Exception as e:
        print(f"[ERROR] Algorithm validation failed: {str(e)}")
        return False

async def main():
    """Main startup routine."""
    print("Alabama Auction Watcher Backend API Startup")
    print("=" * 50)

    # Check working directory
    if not os.path.exists("scripts/utils.py"):
        print("[ERROR] Must run from auction root directory (where scripts/utils.py exists)")
        return False

    # Check dependencies
    if not check_dependencies():
        return False

    # Validate Python algorithms
    if not await validate_python_scripts():
        return False

    # Initialize database
    if not await initialize_database():
        return False

    print("\n[SUCCESS] Initialization complete!")
    print("[INFO] API will be available at: http://localhost:8001")
    print("[INFO] API docs will be available at: http://localhost:8001/api/docs")
    print("[INFO] Health check: http://localhost:8001/health")
    print("\n[INFO] Press Ctrl+C to stop the server\n")

    # Start server (this will block until interrupted)
    start_server()

    return True

if __name__ == "__main__":
    try:
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Run main function
        success = asyncio.run(main())
        sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        print("\n[INFO] Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Startup failed: {str(e)}")
        sys.exit(1)
