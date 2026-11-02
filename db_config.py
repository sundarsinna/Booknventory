import os
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "postgres")

try:
    _secrets = st.secrets
except StreamlitSecretNotFoundError:
    _secrets = {}

DB_PASSWORD = (
    os.getenv("DB_PASSWORD")
    or os.getenv("PGPASSWORD")
    or _secrets.get("DB_PASSWORD")
)
DB_SCHEMA = os.getenv("DB_SCHEMA", "BookInventory")
