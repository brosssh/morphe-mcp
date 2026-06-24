import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REPOS = {
    "official-patches": Path("official-patches"),
    # Shared library consumed by every bundle below (app.morphe:morphe-patches-library /
    # app.morphe:morphe-extensions-library). See knowledge/SYSTEM.MD for how a bundle adds it.
    "official-patches-library": Path("official-patches-library"),
    "official-patcher": Path("official-patcher"),
    "brosssh-patches": Path("brosssh-patches"),
    "hoodles-patches": Path("hoodles-patches"),
    # Unofficial, brosssh-published library extending official-patches-library with
    # Instagram-specific shared code. Used by brosssh-patches.
    "instagram-morphe-patches-library": Path("instagram-morphe-patches-library"),

}

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8080"))
