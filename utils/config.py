"""Reads settings from environment variables, a local .env file, or Streamlit secrets.
API keys are never stored in source code."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:  # python-dotenv is optional at runtime
    pass


def get(key, default=None):
    value = os.environ.get(key)
    if value:
        return value
    try:
        import streamlit as st
        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:  # no secrets file configured
        pass
    return default
