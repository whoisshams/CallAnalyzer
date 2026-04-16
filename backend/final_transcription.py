from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

with open("/Users/shamsanjum/Skill/Projects/CallRecordingAnalyzer/backend/transcription_sample.txt", "r") as f:
    transcript = f.read()
response = client.responses.create(
    model="gpt-4o",
    input=[
        {
            "role": "system",
            "content":"You are an expert at reading interview transcripts. Your job is to read the transcript and reformat it by labeling each person's speech with either 'Interviewer:' or 'Interviewee:'. Each speaker's turn should be on a new line.This is the transcript:{transcript}"
        },
        {
            "role": "user",
            "content": f"Here is the transcript:\n\n{transcript}"
        }
    ]
)
print(response.output_text)