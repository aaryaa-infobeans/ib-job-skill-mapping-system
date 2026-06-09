#!/usr/bin/env python3
"""Script to start the TruLens dashboard."""

import os
import sys
import argparse
import logging
import warnings

# Silence noisy trulens warnings and deprecations
warnings.filterwarnings("ignore", category=DeprecationWarning, module="trulens")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="trulens_eval")
logging.getLogger("trulens.core.utils.imports").setLevel(logging.ERROR)
logging.getLogger("trulens_eval.utils.imports").setLevel(logging.ERROR)

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
        # Prepend the virtual environment's bin directory to PATH so that
        # TruLens starts the correct Streamlit installation.
        venv_bin = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "venv", "bin"))
        os.environ["PATH"] = f"{venv_bin}{os.path.pathsep}{os.environ.get('PATH', '')}"
        logger.info(f"Prepended {venv_bin} to PATH for streamlit execution")
        
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
