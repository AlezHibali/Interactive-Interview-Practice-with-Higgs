# higgs_client.py
import base64
import io
import os
import subprocess
import uuid
import wave
from openai import OpenAI
from config import BOSON_API_KEY, BOSON_API_BASE, AUDIO_UNDERSTANDING_MODEL, AUDIO_GENERATION_MODEL, DEFAULT_VOICE

# Initialize OpenAI-compatible client pointing at Boson
client = OpenAI(api_key=BOSON_API_KEY, base_url=BOSON_API_BASE)


def encode_bytes_to_base64(b: bytes) -> str:
    return base64.b64encode(b).decode("utf-8")


def file_bytes_to_wav_bytes(input_bytes: bytes, input_ext: str = "webm"):
    """
    Convert an input audio blob (webm/ogg/mp3) to WAV bytes using ffmpeg.
    Requires ffmpeg installed. Returns wav bytes.
    """
    tmp_in = f"./tmp/{uuid.uuid4().hex}_in.{input_ext}"
    tmp_out = f"./tmp/{uuid.uuid4().hex}_out.wav"
    with open(tmp_in, "wb") as f:
        f.write(input_bytes)

    # ffmpeg -y -i input -ar 16000 -ac 1 output.wav
    cmd = ["ffmpeg", "-y", "-i", tmp_in, "-ar", "16000", "-ac", "1", tmp_out]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    with open(tmp_out, "rb") as f:
        wav_bytes = f.read()

    # clean up
    try:
        os.remove(tmp_in)
        os.remove(tmp_out)
    except Exception:
        pass

    return wav_bytes


def transcribe_wav_bytes(wav_bytes: bytes, file_format="wav", system_prompt: str = None):
    """
    Use Boson's higgs-audio-understanding model via chat.completions.
    Audio must be base64-encoded inside the messages as "input_audio".
    Returns the model's textual response according to the system_prompt.
    """
    audio_base64 = encode_bytes_to_base64(wav_bytes)

    # Default system prompt if not provided
    if system_prompt is None:
        system_prompt = "You are an expert audio transcriber and evaluator."

    response = client.chat.completions.create(
        model=AUDIO_UNDERSTANDING_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "input_audio": {"data": audio_base64, "format": file_format}}
                ],
            }
        ],
        max_completion_tokens=4096,
        temperature=0.0,
    )

    return response.choices[0].message.content.strip()


def tts_text_to_wav_bytes(text: str, voice: str = DEFAULT_VOICE):
    """
    Use Boson's audio.speech.create (audio/speech) to generate PCM, then wrap into WAV bytes.
    The openai client supports audio.speech.create for Boson.
    The model returns PCM in response.content; we must write WAV header.
    """
    # Request PCM from service
    resp = client.audio.speech.create(
        model=AUDIO_GENERATION_MODEL,
        voice=voice,
        input=text,
        response_format="pcm"
    )
    pcm_data = resp.content  # bytes of PCM (s16le)
    # Wrap PCM into WAV (mono, 16-bit, 24000 Hz per docs)
    num_channels = 1
    sample_width = 2
    sample_rate = 24000

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    wav_bytes = buf.getvalue()
    return wav_bytes
