# Shared settings for every lab, read from .env.
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

MAIN_MODEL = os.environ.get("MAIN_MODEL", "bedrock/moonshotai.kimi-k2.5")
SYSTEM1_MODEL = os.environ.get("SYSTEM1_MODEL", "ollama/qwen3.5:4b")
SMALL_MODEL = os.environ.get("SMALL_MODEL", "bedrock/moonshotai.kimi-k2.5")
BIG_MODEL = os.environ.get("BIG_MODEL", "bedrock/us.moonshotai.kimi-k3")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
KEV_URL = os.environ.get("KEV_URL", "http://127.0.0.1:8009")


def _pulled_models() -> set[str]:
    response = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
    response.raise_for_status()
    return {model["name"] for model in response.json()["models"]}


def check_ollama(*models: str) -> None:
    """Exit with a one-line fix if Ollama is down or a model isn't pulled."""
    wanted = [m.removeprefix("ollama/") for m in models if "/" not in m.removeprefix("ollama/")]
    if not wanted:
        return
    try:
        pulled = _pulled_models()
    except httpx.HTTPError:
        print(f"Ollama isn't reachable at {OLLAMA_HOST}. Start it with: ollama serve")
        sys.exit(1)
    for model in wanted:
        if model not in pulled and f"{model}:latest" not in pulled:
            print(f"Model {model} isn't pulled. Run: ollama pull {model}")
            sys.exit(1)


def build_model(spec: str):
    """Turn "bedrock/<id>" or "ollama/<name>" into a Strands model (lab 9 needs model objects)."""
    provider, _, name = spec.partition("/")
    if provider == "bedrock":
        from strands.models.bedrock import BedrockModel

        return BedrockModel(model_id=name)
    if provider == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(host=OLLAMA_HOST, model_id=name)
    raise ValueError(f"Model {spec!r} must start with bedrock/ or ollama/")
