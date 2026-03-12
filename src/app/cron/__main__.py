"""Allow `python -m app.cron` to invoke the cron CLI entry point."""
from app.cron.main import main
import sys

sys.exit(main())
