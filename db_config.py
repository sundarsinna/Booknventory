import os
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


try:
    _secrets = st.secrets
except StreamlitSecretNotFoundError:
    _secrets = {}

DB_HOST = os.getenv("DB_HOST") or _secrets.get("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT") or _secrets.get("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME") or _secrets.get("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER") or _secrets.get("DB_USER", "postgres")
DB_PASSWORD = (
    os.getenv("DB_PASSWORD")
    or os.getenv("PGPASSWORD")
    or _secrets.get("DB_PASSWORD")
)
DB_SCHEMA = os.getenv("DB_SCHEMA") or _secrets.get("DB_SCHEMA", "BookInventory")
BOOK_API_URL = os.getenv("BOOK_API_URL") or _secrets.get(
    "BOOK_API_URL",
    "http://127.0.0.1:8002",
)
