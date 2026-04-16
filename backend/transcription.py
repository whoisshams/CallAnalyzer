from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


client = OpenAI(api_key=api_key)
audio_file = open("/Users/shamsanjum/Skill/Projects/CallRecordingAnalyzer/backend/demo_interview.mp3", "rb")

transcription = client.audio.transcriptions.create(
  model="gpt-4o-transcribe", 
  file=audio_file, 
  response_format="json",
  prompt="The following conversation is between a customer and a support agent. The customer will mainly be asking about the services of the hopsital and informations about dcotors appointments."
)

print(transcription.text)

with open("/Users/shamsanjum/Skill/Projects/CallRecordingAnalyzer/backend/transcription_sample.txt", "w") as f:
    f.write(transcription.text)