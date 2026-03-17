import sys
import os
sys.path.insert(0, "src")
from app.settings import settings
print(f"DATABASE_URL: {settings.get_database_url()}")
