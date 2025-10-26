# app.py
import os
import traceback
import io
import wave
import contextlib
import json
import re
from flask import Flask, request, jsonify, send_file
from higgs_client import (
    file_bytes_to_wav_bytes,
    transcribe_wav_bytes,
    tts_text_to_wav_bytes,
)
from datetime import datetime
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from rag_question import PromptingRAGQuestions
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from werkzeug.utils import secure_filename
import tempfile
from llm_client import summarize_interview_llm, summarize_transcript_llm, analyze_question_llm
import openai

UPLOAD_FOLDER = "./uploaded_resumes"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, static_folder="../frontend", static_url_path="/")

# In-memory session store (for demo purposes)
sessions = [
    {
        'timestamp': '2025-10-24T15:30:00',
        'total_score': 4,
        'questions': [
            {
                'question': 'Tell me about yourself?',
                'response': 'I am a software engineer with 5 years of experience...',
                'analysis_content': 'Good explanation of experience and skills.',
                'analysis_delivery': 'Clear voice, moderate pace.',
                'score': 8
            },
            {
                'question': 'What are your strengths?',
                'response': 'I am highly analytical and detail-oriented...',
                'analysis_content': 'Strong examples provided.',
                'analysis_delivery': 'Slightly fast pace but understandable.',
                'score': 7
            },
            {
                'question': 'Describe a challenge you overcame.',
                'response': 'In my last project, we faced a tight deadline...',
                'analysis_content': 'Well-structured story, shows problem-solving.',
                'analysis_delivery': 'Good pacing and clarity.',
                'score': 0
            }
        ],
        'overall_summary': 'Strong content, maintain steady pace in answers. Overall excellent performance.'
    }
]


# -------------------- Routes -------------------- #

@app.route("/")
def index():
    return app.send_static_file("index.html")

def create_vector_db_from_pdf(uploaded_file):
    # Load the PDF using PyPDFLoader
    loader = PyPDFLoader(uploaded_file)
    documents = loader.load()

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(documents)

    # Create FAISS vector DB
    embeddings = OpenAIEmbeddings()
    vector_db = FAISS.from_documents(chunks, embeddings)

    return vector_db

rag_generator = PromptingRAGQuestions()  # default stateless

def clean_question_response(raw_text):
    """
    Ensures the question response is a proper Python list of dicts.
    Handles nested JSON inside 'question' fields and strips ```json``` markers.
    """
    import re, json

    # If input is already a list (like [{'question': '...' }]), convert inner strings
    if isinstance(raw_text, list):
        cleaned_list = []
        for item in raw_text:
            if isinstance(item, dict) and "question" in item:
                q = item["question"]
                # Strip ```json``` or ``` markers
                q = re.sub(r"```(?:json)?\s*", "", q).replace("```", "").strip()
                # Try to parse it if it's a JSON array
                try:
                    parsed = json.loads(q)
                    if isinstance(parsed, list) and all("question" in qd for qd in parsed):
                        cleaned_list.extend(parsed)
                    else:
                        cleaned_list.append({"question": q})
                except json.JSONDecodeError:
                    cleaned_list.append({"question": q})
            else:
                cleaned_list.append(item)
        return cleaned_list

    # If raw_text is a string
    if isinstance(raw_text, str):
        raw_text = re.sub(r"```(?:json)?\s*", "", raw_text).replace("```", "").strip()
        try:
            questions = json.loads(raw_text)
            if isinstance(questions, list) and all(isinstance(q, dict) and "question" in q for q in questions):
                return questions
        except json.JSONDecodeError:
            pass

    # fallback
    return []


@app.route("/question", methods=["POST"])
def question():
    try:
        role = request.form.get("role", "software engineer")
        additional_note = request.form.get("additional_note", "")

        resume_file = request.files.get("resume")

        vector_db = None
        if resume_file:
            filename = secure_filename(resume_file.filename)
            resume_path = os.path.join(UPLOAD_FOLDER, filename)
            resume_file.save(resume_path)
            vector_db = create_vector_db_from_pdf(resume_path)

        # Generate questions
        rag_generator_with_resume = PromptingRAGQuestions(vector_db=vector_db)
        questions_list = rag_generator_with_resume.generate_questions(role, additional_note)

        if isinstance(questions_list, list) and len(questions_list) == 1:
            questions_list = questions_list[0]['question']

        # Clean output: ensure it's always a Python list of dicts
        if isinstance(questions_list, str):
            questions_list = clean_question_response(questions_list)

        # By now, questions_list is a proper Python list
        return jsonify({"questions": questions_list})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/tts", methods=["POST"])
def tts():
    try:
        data = request.json or {}
        text = data.get("text")
        voice = data.get("voice", "en_woman_1")
        if not text:
            return jsonify({"error": "text required"}), 400

        wav_bytes = tts_text_to_wav_bytes(text, voice=voice)
        return send_file(
            io.BytesIO(wav_bytes),
            mimetype="audio/wav",
            as_attachment=False,
            download_name="tts.wav"
        )
        # # Streaming Version
        # # TODO: add voice in streaming
        # def generate():
        #     """
        #     Generator to stream PCM16 audio chunks from Boson.
        #     """
        #     import base64, subprocess

        #     proc = subprocess.Popen(
        #         ["ffplay", "-f", "s16le", "-ar", "24000", "-i", "-", "-nodisp", "-autoexit", "-loglevel", "error"],
        #         stdin=subprocess.PIPE,
        #     )

        #     stream = client.chat.completions.create(
        #         model="higgs-audio-generation-Hackathon",
        #         messages=[
        #             {"role": "system", "content": "Convert the following text from the user into speech."},
        #             {"role": "user", "content": text},
        #         ],
        #         modalities=["text", "audio"],
        #         audio={"format": "pcm16"},
        #         stream=True,
        #         max_completion_tokens=2000,
        #     )

        #     try:
        #         for chunk in stream:
        #             delta = getattr(chunk.choices[0], "delta", None)
        #             audio = getattr(delta, "audio", None)
        #             if not audio:
        #                 continue
        #             data = base64.b64decode(audio["data"])
        #             if proc.poll() is None:
        #                 proc.stdin.write(data)
        #                 proc.stdin.flush()
        #             yield data  # stream chunk to client
        #     finally:
        #         if proc.stdin:
        #             try: proc.stdin.close()
        #             except BrokenPipeError: pass
        #         proc.wait()

        # return Response(generate(), mimetype="audio/wav")
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/upload_answer", methods=["POST"])
def upload_answer():
    try:
        if "file" not in request.files:
            return jsonify({"error": "file required"}), 400
        f = request.files["file"]
        filename = f.filename or "answer"
        content = f.read()
        ext = filename.split(".")[-1].lower()

        # Convert to wav if needed
        if ext not in ("wav", "wave"):
            wav_bytes = file_bytes_to_wav_bytes(content, input_ext=ext if ext else "webm")
        else:
            wav_bytes = content

        # Get audio duration
        duration = None
        try:
            with contextlib.closing(wave.open(io.BytesIO(wav_bytes), 'rb')) as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)
        except Exception:
            duration = None

        # -------------------- Separate API calls -------------------- #

        # 1. Transcribe audio
        transcript = transcribe_wav_bytes(
            wav_bytes,
            file_format="wav",
            system_prompt="Please transcribe this audio exactly as spoken."
        ).strip()

        # 2. Analyze audio (speaker characteristics, tone, background noise, etc.)
        analysis_text = transcribe_wav_bytes(
            wav_bytes,
            file_format="wav",
            system_prompt=(
                "Analyze the audio for speaker characteristics, clarity, tone, "
                "background noise, pitch, speech rate, and pronunciation. "
                "Do NOT include the transcript, only the analysis."
            )
        ).strip()

        analysis = {
            "duration_seconds": duration,
            "analysis_text": analysis_text,
        }

        return jsonify({
            "transcript": transcript,
            "analysis": analysis
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/summary", methods=["POST"])
def summary():
    try:
        transcript = request.json.get("transcript", "")
        if not transcript:
            return jsonify({"error": "transcript required"}), 400
        result = summarize_transcript_llm(transcript)
        return jsonify({"summary": result})
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

@app.route("/analyze_question", methods=["POST"])
def analyze_question():
    try:
        data = request.json or {}
        question = data.get("question", "")
        response = data.get("response", "")

        if not question or not response:
            return jsonify({"error": "question and transcript required"}), 400

        raw_analysis = analyze_question_llm(question, response)

        text = raw_analysis["text"]

        # Step 1: Remove everything before </think>
        if "</think>" in text:
            raw_analysis = text.split("</think>", 1)[1]

        # Step 2: Extract analysis_content
        match_content = re.search(r'"analysis_content"\s*:\s*"(.*?)"\s*,\s*"analysis_delivery"', raw_analysis, re.DOTALL)
        analysis_content = match_content.group(1) if match_content else ""

        # Step 3: Extract analysis_delivery
        match_delivery = re.search(r'"analysis_delivery"\s*:\s*"(.*?)"\s*,\s*"score"', raw_analysis, re.DOTALL)
        analysis_delivery = match_delivery.group(1) if match_delivery else ""

        # Step 4: Extract score (integer)
        match_score = re.search(r'"score"\s*:\s*(\d+)', raw_analysis)
        score = int(match_score.group(1)) if match_score else None

        return jsonify({
            "analysis_content": analysis_content,
            "analysis_delivery": analysis_delivery,
            "score": score
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

@app.route("/summarize_interview", methods=["POST"])
def summarize_interview():
    try:
        data = request.get_json(force=True)  # force parse JSON
        questions = data.get("questions", [])
        if not questions:
            return jsonify({"error": "questions required"}), 400
        result = summarize_interview_llm(questions)

        # process result
        # Keep only content after </think>
        result = result["text"]
        if "</think>" in result:
            result = result.split("</think>", 1)[1].strip()

        # Try parsing as JSON (in case it's a JSON string)
        try:
            summary = json.loads(result)
        except json.JSONDecodeError:
            summary = {"text": result}  # fallback as plain text

        # Convert lists to HTML strings
        for key in ["strengths", "weaknesses", "tips"]:
            if key in summary and isinstance(summary[key], list):
                summary[key] = "<br>".join(summary[key])

        # Now summary is safe to send to frontend
        return jsonify({"overall_summary": summary})
    
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# === Endpoint: save session ===
@app.route("/save_session", methods=["POST"])
def save_session():
    data = request.json
    questions = data.get("questions", [])
    
    if not questions or len(questions) != 3:
        return jsonify({"error": "Must have exactly 3 questions"}), 400

    total_score = sum(q.get("score", 0) for q in questions)
    timestamp = datetime.now().isoformat()
    overall_summary = data.get("overall_summary", "")

    session = {
        "timestamp": timestamp,
        "total_score": total_score,
        "questions": questions,
        "overall_summary": overall_summary
    }

    sessions.append(session)
    return jsonify({"status": "success", "session": session})

# === Endpoint: get session history ===
@app.route("/session_history", methods=["GET"])
def get_session_history():
    return jsonify({"sessions": sessions})


# === Endpoint: give comment ===
@app.route("/give_comment", methods=["GET"])
def give_comment():
    try:
        comments = []

        client = openai.OpenAI()

        for session in sessions:
            summary_text = session.get("overall_summary", "")

            # Prompt GPT-4o-mini
            prompt = f"""
You are a friendly interview coach. 
Based on this session summary, give a 2-3 line comment that encourages the candidate or gives a small tip:

Summary: {summary_text}
"""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a friendly interview coach."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=60
            )

            comment_text = response.choices[0].message.content.strip()
            comments.append({
                "timestamp": session["timestamp"],
                "comment": comment_text
            })

        return jsonify({"comments": comments})

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -------------------- Main -------------------- #
if __name__ == "__main__":
    print("BOSON_API_BASE:", os.getenv("BOSON_API_BASE"))
    app.run(host="0.0.0.0", port=5000, debug=True)
