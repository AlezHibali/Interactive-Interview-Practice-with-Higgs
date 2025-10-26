# config.py
import os

# Boson hackathon settings (OpenAI-compatible endpoints)
BOSON_API_BASE = os.getenv("BOSON_API_BASE", "https://hackathon.boson.ai/v1")
BOSON_API_KEY  = os.getenv("BOSON_API_KEY", "")

# Models (change if hackathon gives different model names)
AUDIO_UNDERSTANDING_MODEL = "higgs-audio-understanding-Hackathon"
AUDIO_GENERATION_MODEL    = "higgs-audio-generation-Hackathon"
QWEN_MODEL                = "Qwen3-Omni-30B-A3B-Thinking-Hackathon"

# TTS voice (one of the supported voices from docs)
DEFAULT_VOICE = os.getenv("HIGGS_TTS_VOICE", "en_woman_1")
