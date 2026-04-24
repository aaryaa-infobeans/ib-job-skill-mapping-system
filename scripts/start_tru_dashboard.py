#!/usr/bin/env python3
"""Script to start the TruLens dashboard."""

import os
import sys
import argparse
import logging

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from app.services.trulens_service import trulens_service
except ImportError:
    print("❌ Error: Could not import TruLensService. Make sure you are in the project root and PYTHONPATH is set correctly.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Start the TruLens dashboard.")
    parser.add_argument("--port", type=int, default=8501, help="Port to run the dashboard on (default: 8501)")
    
    args = parser.parse_args()
    
    print(f"🦑 Starting TruLens Dashboard on port {args.port}...")
    print(f"🔗 Once started, visit: http://localhost:{args.port}")
    
    try:
        trulens_service.start_dashboard(port=args.port)
        # Keep the script running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping TruLens Dashboard...")
        trulens_service.stop_dashboard()
    except Exception as e:
        logger.error(f"Failed to run TruLens dashboard: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
