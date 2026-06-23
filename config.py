import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

REPOS = {
    "official-patches": Path("official-patches"),
    "official-patches-library": Path("official-patches-library"),
    "official-patcher": Path("official-patcher"),
    "brosssh-patches": Path("brosssh-patches"),
    "hoodles-patches": Path("hoodles-patches"),

}

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

HOST = os.getenv("MCP_HOST", "0.0.0.0")
PORT = int(os.getenv("MCP_PORT", "8080"))
