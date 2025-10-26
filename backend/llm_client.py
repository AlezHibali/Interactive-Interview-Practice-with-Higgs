# llm_client.py
import json
from openai import OpenAI
from config import BOSON_API_KEY, BOSON_API_BASE, QWEN_MODEL
from model_prompts import build_interview_prompt, build_question_prompt, build_summary_prompt, DELIMITER

client = OpenAI(api_key=BOSON_API_KEY, base_url=BOSON_API_BASE)


# No longer used
def generate_question(role="software engineer", difficulty="intermediate", additional_note=""):
    """
    Generates 3 relevant interview questions using a structured prompt (persona + COT + format + few-shot).
    Returns a list of dicts: [{"main": ..., "followup": ...}, ...].
    """
    delimiter = "####"

    persona_pattern = f"""
# Persona
You are a professional interviewer AI specializing in realistic mock interviews for different roles.
Your goal is to create challenging, context-aware interview questions for a given job role ({role}),
considering any additional context or notes provided by the user.
The query will be delimited with four hashtags (i.e., {delimiter}).
"""

    cot_pattern = f"""
# Chain of Thought
Step 1: {delimiter} Read and interpret the given role, difficulty, and additional note carefully.
Step 2: {delimiter} Create three unique interview questions that each assess different aspects (technical, behavioral, or reasoning).
Step 3: {delimiter} Add a one-line follow-up for each question that encourages deeper thinking.
Step 4: {delimiter} Respond strictly in JSON format as defined below.
"""

    format_template_pattern = """
# Format Template
Respond exactly in the following JSON structure:
{
  "questions": [
    {"main": "Question text...", "followup": "Follow-up question..."},
    {"main": "Question text...", "followup": "Follow-up question..."},
    {"main": "Question text...", "followup": "Follow-up question..."}
  ]
}
Each question should be short (under 25 words) and natural.
"""

    few_shot_pattern = """
# Few-Shot Example
You are a professional interviewer for a Data Scientist position.
Generate exactly 3 concise behavioral/technical interview questions for a Intermediate candidate.
Include a one-line follow-up question for each.
Include the additional note if relevant: Focus on model interpretability and ML deployment

Return **only valid JSON**, no explanations, no text outside JSON.

Output:
{
  "questions": [
    {
      "main": "How would you explain model interpretability to non-technical stakeholders?"
    },
    {
      "main": "Describe a situation where you improved an ML model’s performance."
    },
    {
      "main": "What steps do you take to ensure reliability in ML deployment?"
    }
  ]
}
"""

    user_prompt = f"""
You are a professional interviewer for a {role} position.
Generate exactly 3 concise behavioral/technical interview questions for a {difficulty} candidate.
Include a one-line follow-up question for each.
Include the additional note if relevant: {additional_note}

Return **only valid JSON**, no explanations, no text outside JSON.
Format:
{{
  "questions": [
    {{"main": "Question 1 text"}},
    {{"main": "Question 2 text"}},
    {{"main": "Question 3 text"}}
  ]
}}

"""

    full_prompt = f"{persona_pattern}\n{cot_pattern}\n{format_template_pattern}\n{few_shot_pattern}\n{user_prompt}"

    resp = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": "You are a professional interviewer and question generator."},
            {"role": "user", "content": full_prompt}
        ],
        temperature=0.8,
        max_tokens=2000,
    )

    import json
    try:
        content = resp.choices[0].message.content.strip()
        result = json.loads(content)
        return result["questions"]
    except Exception as e:
        print("Error parsing model output:", e)
        return []

# def summarize_feedback(transcript: str, audio_meta: dict = None):
#     audio_meta = audio_meta or {}
#     prompt = (
#         f"Candidate transcript:\n{transcript}\n\n"
#         f"Audio metadata:\n{audio_meta}\n\n"
#         "Give a short evaluation (3–6 bullet points) about clarity, confidence, pace, structure, and 3 actionable tips. "
#         "Finally give an overall score from 1 to 10."
#     )
#     resp = client.chat.completions.create(
#         model=QWEN_MODEL,
#         messages=[
#             {"role": "system", "content": "You are a helpful professional interview coach."},
#             {"role": "user", "content": prompt},
#         ],
#         temperature=0.25,
#         max_tokens=2000,
#     )
#     return resp.choices[0].message.content.strip()

def call_llm(prompt: str, temperature=0.0):
    resp = client.chat.completions.create(
        model=QWEN_MODEL,
        messages=[
            {"role": "system", "content": "You are an expert interview coach."},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        max_tokens=4096
    )
    content = resp.choices[0].message.content.strip()
    try:
        return json.loads(content)
    except Exception:
        # fallback: return raw text if JSON fails
        return {"text": content}


def summarize_transcript_llm(transcript: str):
    user_input = f"{DELIMITER} Candidate Transcript:\n{transcript}\n{DELIMITER}\nReturn STRICTLY as ONLY JSON output as in few-shot example."
    prompt = build_summary_prompt(user_input)
    return call_llm(prompt)


def analyze_question_llm(question: str, response: str):
    user_input = f"{DELIMITER} Question: {question}\nResponse: {response}\n{DELIMITER}\nReturn STRICTLY as ONLY JSON output as in few-shot example."
    prompt = build_question_prompt(user_input, response)
    return call_llm(prompt)


def summarize_interview_llm(questions: list):
    transcript = ""
    for q in questions:
        transcript += "Question: " + q['question'] + "\n" + "Answer: " + q['response'] + "\n"

    user_input = f"{DELIMITER} Candidate Responses:\n{transcript}\n{DELIMITER}\nReturn STRICTLY as ONLY JSON output as in few-shot example."
    prompt = build_interview_prompt(user_input)
    return call_llm(prompt)

