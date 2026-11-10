import os
import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import re
from typing import Optional
from typing import List
import pandas as pd
import json
from fastapi.responses import FileResponse
from typing import Any, Dict
from fastapi.middleware.cors import CORSMiddleware
from langgraph_model import app_lg
load_dotenv()

# Configure the AI model with the API key
genai.configure(api_key=os.getenv("API_KEY"))

API_URL = os.getenv("API_URL")


model = genai.GenerativeModel("gemini-2.5-flash")


# Create the FastAPI app instance
app = FastAPI()
templates = Jinja2Templates(directory="templates")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # "*" allows all domains, for development purposes
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

initial_state = {

    "user_message": "",

    "chat_history": [],

    "code": [],

    "response": ""
}

def extract_dataframe_from_response(ai_response: str) -> Optional[list]:
    """
    Extract the schedule table as a CSV string from the AI response and convert it to a DataFrame.
    Returns the table as a list of dictionaries (for easy JSON conversion).
    """
    # Look for "schedule_table" in the response using regex and capture the CSV-like table
    table_pattern = r"schedule_table\s*=\s*(.*?)(?=\n\s*\n|\Z)"

    match = re.search(table_pattern, ai_response, re.DOTALL)
    if match:
        # Extracted table string
        table_str = match.group(1).strip()

        # Convert the table string into a pandas DataFrame
        try:
            # Read the CSV string into a DataFrame
            from io import StringIO
            df = pd.read_csv(StringIO(table_str))
            
            # Convert DataFrame to list of dictionaries
            return df.to_dict(orient="records")
        except Exception as e:
            print(f"Error parsing schedule table: {e}")
            return None
    return None

def extract_json_from_llm(text):
    try:
        # Extract JSON array using regex
        match = re.search(r"\[\s*{.*}\s*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError("No JSON found")
    except Exception as e:
        raise ValueError(f"JSON extraction failed: {str(e)}")
    
# Store chat sessions
chat_sessions = {}
state_sessions = {}




# Pydantic models for request and response validation
class ChatRequest(BaseModel):
    student_id: str
    message: str
    finalize: bool = False

class ChatResponse(BaseModel):
    response: str
    code: str

# Function to build the AI prompt
def build_prompt(history, question):
    result = app_lg.invoke({

    "user_message": question,

    "chat_history": history,

    "code": "",

    "response": ""
})
    return result["response"],result["code"]



# Route to handle the chat functionality
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    student_id = request.student_id
    print("============")
    print(student_id)
    print("============")
    message = request.message
    finalize = request.finalize
   
    # Retrieve chat history or create a new one if not found
    history = chat_sessions.get(student_id, [])

   
    



    # Build the AI prompt based on student's message
    prompt,code = build_prompt(history, message)

    

    # Call the AI model to generate content based on the prompt
    

    ai_reply = prompt

    

    # Update chat history
    history.append({"student": message})
    history.append({"ai": ai_reply})

    # Store the updated history for the student
    chat_sessions[student_id] = history


    
 
    return ChatResponse(response=ai_reply,code=code)

# Optional: Route to serve the homepage (if needed)
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("chat.html",{ "request": request,"api_url":API_URL})

# POST endpoint to handle the form submission and render the chat.html template
# Define a Pydantic model to handle incoming JSON data
class SubmitInfoRequest(BaseModel):
    student_id: str
    message: str
    name: str
    primary_care_done: int
    electives_weeks_done: int
    electives_list_completed: list[str]  # This is an array of course numbers
    electives_weeks_inperson: int
    electives_weeks_virtual: int
    electives_within_CHM: int
    career_goal: str
    finalize: bool

@app.post("/submit_info", response_class=HTMLResponse)
async def submit_info(request: Request, data: SubmitInfoRequest):
    # Extract data from the request
    student_id = data.student_id
    message = data.message
    name = data.name
    primary_care_done = data.primary_care_done
    electives_weeks_done = data.electives_weeks_done
    electives_list_completed = data.electives_list_completed
    electives_weeks_inperson = data.electives_weeks_inperson
    electives_weeks_virtual = data.electives_weeks_virtual
    electives_within_CHM = data.electives_within_CHM
    career_goal = data.career_goal
    finalize = data.finalize

    # Now you can pass this data to the template or process it as needed
    return templates.TemplateResponse(
        "chat.html", 
        {
            "request": request,
            "student_id": student_id,
            "message": message,
            "name": name,
            "primary_care_done": primary_care_done,
            "electives_weeks_done": electives_weeks_done,
            "electives_list_completed": electives_list_completed,
            "electives_weeks_inperson": electives_weeks_inperson,
            "electives_weeks_virtual": electives_weeks_virtual,
            "electives_within_CHM": electives_within_CHM,
            "career_goal" : career_goal,
            "API_URL": API_URL
        }
    )
# Run the app (this is for when using `uvicorn` directly, typically you use `uvicorn main:app --reload`)