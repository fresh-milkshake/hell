from pathlib import Path

PROJECT_PATH = Path(__file__).resolve().parent.parent

DATABASE_FILE_NAME = "database.db"
DATABASE_PATH = PROJECT_PATH / DATABASE_FILE_NAME
