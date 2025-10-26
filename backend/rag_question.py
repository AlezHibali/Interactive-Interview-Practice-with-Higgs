# rag_question.py
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
import re
import json

class PromptingRAGQuestions:
    def __init__(self, vector_db=None, top_k=5):
        """
        Stateless RAG for generating interview questions
        """
        self.delimiter = "####"
        self.top_k = top_k
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature = 0.0)

        # Default to empty FAISS if no vector DB is provided
        if vector_db is None:
            embedding_model = OpenAIEmbeddings()
            self.vector_db = FAISS.from_texts([""], embedding_model)
        else:
            self.vector_db = vector_db

        self.retriever = self.vector_db.as_retriever(search_kwargs={"k": self.top_k})

        # Prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("human", "{prompt_text}"),
        ])

        # Static templates
        self.persona = f"""
# Persona
You are a professional interviewer designed to generate concise, relevant interview questions for candidates. 
Focus on clarity, relevance, and role-specific requirements. The query will be delimited by {self.delimiter}.
        """

        self.cot = f"""
# Chain of Thought
Step 1: {self.delimiter} Use the candidate's resume and additional notes as context.
Step 2: {self.delimiter} Generate role-appropriate, challenging, but answerable questions.
Step 3: {self.delimiter} Format the output strictly as JSON, with 3 questions, no follow-ups. First 2 from personal experiences and last one is general question.
        """

        self.few_shot = """
# Few-Shot Example
Candidate info: "Resume shows experience in backend development and team leadership."
Output: [
  {"question": "Describe a backend system you designed and the challenges faced."},
  {"question": "How did you handle team conflicts during a project?"},
  {"question": "Explain how you optimize database queries in high-traffic applications."}
]
        """

    def _generate_prompt(self, role, additional_note=""):
        """
        Combine persona, CoT, few-shot, and candidate info into a single prompt
        """
        user_input = (
            f"{self.delimiter} Generate 3 interview questions for a candidate applying as {role}."
            "The first two questions should be related to personal experience if possible. The last question should be general technical question."
            f"Additional notes: {additional_note}\n {self.delimiter}\n"
            f"Return strictly as JSON list of objects: [{{'question': ...}}, ...]"
        )

        # Retrieve top-k relevant documents from vector store
        retrieved_docs = self.retriever.get_relevant_documents(user_input)
        domain_info_plain = "\n".join(doc.page_content for doc in retrieved_docs)
        domain_info = f"""
# Inject Domain Information
Here is the retrieved passage:
{{
    "{domain_info_plain}"
}}
"""

        # Final prompt combines persona, CoT, few-shot, domain info, and user input
        full_prompt = f"{self.persona}\n{domain_info}\n{self.cot}\n{self.few_shot}\n{user_input}"
        return full_prompt

    def generate_questions(self, role, additional_note=""):
        prompt_text = self._generate_prompt(role, additional_note)

        # Run through LLM
        rag_chain = RunnablePassthrough() | self.prompt | self.llm | StrOutputParser()
        response = rag_chain.invoke(prompt_text)

        # Parse JSON safely
        try:
            questions_list = json.loads(response)
            if isinstance(questions_list, list):
                # Keep only 'question' fields
                return [{"question": q.get("question", "").strip()} for q in questions_list]
        except Exception:
            # Fallback: single-question list
            return [{"question": response.strip()}]
