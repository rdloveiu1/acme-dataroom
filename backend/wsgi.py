from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402 (must load .env before importing app config)

app = create_app()
