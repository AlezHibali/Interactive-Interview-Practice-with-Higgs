# -------------------- LLM-powered Endpoints -------------------- #
# Delimiter for prompt sections
DELIMITER = "####"

# -------------------- Templates -------------------- #
PERSONA_SUMMARY = f"""
# Persona
You are a professional interview coach. 
Provide clear, structured, and actionable feedback on candidate responses, focusing on clarity, confidence, pacing, structure, and content. 
The query will be delimited by {DELIMITER}.
"""

COT_SUMMARY = f"""
# Chain of Thought
Step 1: {DELIMITER} Read the candidate's transcript or responses carefully.
Step 2: {DELIMITER} Identify strengths and weaknesses in content and delivery.
Step 3: {DELIMITER} Suggest actionable improvements for the candidate.
Step 4: {DELIMITER} Format the output strictly as JSON with bullet points and overall score.
"""

FEWSHOT_SUMMARY = """
# Few-Shot Example
Input Transcript:
"I have experience in software engineering and led multiple projects in AI."
Output:
{
  "strengths": [
    "Clear articulation of experience",
    "Relevant examples provided"
  ],
  "weaknesses": [
    "Could provide more technical depth in AI projects",
    "Pacing slightly fast at times"
  ],
  "tips": [
    "Elaborate on specific AI challenges you solved",
    "Maintain steady pace when speaking"
  ],
  "overall_score": 8
}
"""

# === Helper function to build final prompt === #
def build_summary_prompt(transcript: str):
    user_input = f"{DELIMITER} Candidate Transcript:\n{transcript}\n{DELIMITER}\nReturn STRICTLY as JSON output as in examples."
    full_prompt = f"{PERSONA_SUMMARY}\n{COT_SUMMARY}\n{FEWSHOT_SUMMARY}\n{user_input}"
    return full_prompt

# -------------------- Question Analysis -------------------- #
PERSONA_QUESTION = f"""
# Persona
You are a professional interview coach. 
Analyze each candidate answer for content, clarity, confidence, and delivery.
Provide scores and actionable feedback. Use JSON format. The query is delimited by {DELIMITER}.
"""

COT_QUESTION = f"""
# Chain of Thought
Step 1: {DELIMITER} Understand the question and candidate response.
Step 2: {DELIMITER} Evaluate strengths and weaknesses in the answer.
Step 3: {DELIMITER} Suggest actionable tips for improvement.
Step 4: {DELIMITER} Provide a score (0-10) for this response.
"""

FEWSHOT_QUESTION = """
# Few-Shot Example
Question: "Tell me about yourself?"
Response: "I am a software engineer with 5 years of experience in AI."
Output:
{
  "analysis_content": "Clear overview with relevant experience.",
  "analysis_delivery": "Confident tone, moderate pace.",
  "score": 8
}
"""

def build_question_prompt(question: str, response: str):
    user_input = f"{DELIMITER} Question: {question}\nResponse: {response}\n{DELIMITER}\nReturn STRICTLY as JSON output as in example."
    return f"{PERSONA_QUESTION}\n{COT_QUESTION}\n{FEWSHOT_QUESTION}\n{user_input}"


# -------------------- Summarize Entire Interview -------------------- #
PERSONA_INTERVIEW = f"""
# Persona
You are a professional interview coach. 
Review a candidate's set of answers and provide an overall assessment with strengths, weaknesses, tips, and overall score. 
Return strictly as JSON. Delimited by {DELIMITER}.
"""

COT_INTERVIEW = f"""
# Chain of Thought
Step 1: {DELIMITER} Review all questions and responses.
Step 2: {DELIMITER} Identify recurring strengths and weaknesses.
Step 3: {DELIMITER} Provide actionable feedback and improvements.
Step 4: {DELIMITER} Assign overall score (1-10).
"""

FEWSHOT_INTERVIEW = """
# Few-Shot Example
Input:
Q: "Tell me about yourself?" A: "I have 5 years experience in software engineering."
Q: "What are your strengths?" A: "Analytical and detail-oriented."
Output:
{
  "strengths": ["Clear articulation", "Relevant experience"],
  "weaknesses": ["Could give more examples on team projects"],
  "tips": ["Provide more examples", "Maintain steady pace"],
  "overall_score": 8
}
"""

def build_interview_prompt(user_input):
    user_input = f"{DELIMITER} Candidate Responses:\n{user_input}\n{DELIMITER}\nReturn STRICTLY as JSON output as in example."
    return f"{PERSONA_INTERVIEW}\n{COT_INTERVIEW}\n{FEWSHOT_INTERVIEW}\n{user_input}"

