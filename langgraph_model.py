from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import json
from rag import retriever
import re
from html import escape


load_dotenv()

google_api_key = os.getenv("API_KEY")

gemini = ChatGoogleGenerativeAI(
    model="gemini-3.7-flash",
    temperature=0,
    google_api_key=google_api_key
)



class SchedulerState(TypedDict):

    # Current user message
    user_message: str

    # Conversation memory
    chat_history: List[str]

    # Persistent schedule
    code: Dict[str, Any]

    # Final answer
    response: str

initial_state = {

    "user_message": "",

    "chat_history": [],

    "code": {},

    "response": ""
}

def context_managaer(state):
    print("context")
    prompt = f"""

    We are running a chatbot to help users exceute codes from BGLR

    This is  chat history until now: {state ['chat_history']} 
    
    This is User's current message:
    {state['user_message']}

    Sumarize the chat history to include important elements (keep it short 5-6 sentences)
    Make sure to keep the last 4 turns  
    and also tell in detail current context about what student needs

    Output should look like this

    Chat history : <explain the chat history as mentioned above>
    Current context or ask : <explain the current context>

    """
    response = gemini.invoke(prompt)

    #print(response.text)

    if os.getenv("ENV") == "prod":
        res = response.content
    else:
        res = response.text

    return {
        "chat_history": res,
    }


    
def schedule_agent(state):

    print("schedule")

  


    result = f"""
    You are a medical school scheduling assistant. You must assist 4th year medical students to schedule the following across 42 weeks. 
    1. ICU (can only be done in 4th year)
    2. Primary care (If not completed in their 3rd year)
    3. Electives (18 weeks - no of weeks completed in 3rd year)

    ## NOTE - Primary care courses can be considered for electives but that does not mean that by choosing a primary care course will reduce a 18 week elective course requirement they are separate. 4 weeks of primary and 18 weeks of electives are sepaarte.

    Guidelines for planning for each is as follows
    {guidelines}
    - If Students ask to schedule for AWAY Rotation mention  AWAY(campus in which they want to do rotation) under the "course" and under "notes" mention the dates .
    - 7/6-7/31/2026 this week is either Summer break or ASK 3 dont schedule anything else here
    - If student wants to schedule two different coursses for a 4 week block then show both the courses comma separated under course. for example schedule ask 4 for first two weeks and phd 619 for last two weeks of 8/31-9/25/2026. then mention ASK 4, PHD 619 under course
    
    IMPORTANT ELECTIVES REQUIREMENTS CHECK
    - Every time a student schedules for electives check if atleast 12 weeks of the eletives are in person
    - Whether atleast 8 weeks are within CHM system and not away rotation. out of the 8 weeks whether atleast 4 weeks are in person.
    - does not matter if student has more than 6 weeks of virtual electives only 6 weeks will count towards graduation requirements and the student should still schedule 12 weeks of in person electives
    
    
    Student Prior Information is as follows: {state["student_state"]}
    Student Message : {state["user_message"]}

    Course Knowledge Agent results to give you idea on courses (this is just information on course not what student wants)- {state["course_results"]}

    Please edit {state["schedule"]} to reflect the requests. 

    ALWAYS MENTION THE COURSE NUMBER AS IT IS under course 
    IF STUDENT IS SCHEDULE PRIMARY CARE PLEASE MENTION "Primary Care" in notes

    REMEMBER YOU ONLY EDIT THE SCHEDULE BASED ON WHAT STUDENT WANTS YOU CANNOT PUT YOUR RECOMMENDATIONS DIRECTLY INTO SCHEDULE UNLESS THE STUDENT SAY SO

    RESPONSE FORMAT STRICTLY JSON ONLY 

    {state["schedule"]}

    """

    response = gemini.invoke(result)
    if os.getenv("ENV") == "prod":
        res = response.content
    else:
        res = response.text
    result = json.loads(res)

    print(result)

    print("========")

    print(state["student_state"])

   

   

    return {

        "schedule": result,
      

       
    }

  

def recommend_agent(state):

    print("course_knowledge")


    result = f"""
    You are a Course Knowledge Agent who has knowledge of all the medical courses for electives, ICU and PCP

    Current context and chat history for better understanding: 
        {state['chat_history']}

    Elective Course options are {electives} Please make sure they have the prerequisites to take up a certain elective and only 6 weeks of online only electives and non-clinical electives cannot be continuously for 4 weeks only 2 weeks consecutive allowed
    ICU options are {icu_options}
    Primary care selective options are {pc_options}
    You can let them know some rules on the selection based on {guidelines}

    student message: {state["user_message"]}

    Answer to the student based on the knowledge you have. Just use the knowledge you have. DO NOT Hallucinate. Answer in few sentences please

    Also give all information regarding the courses mentioned in {state["student_state"]} and {state["schedule"]} so the scheduling agent has all idea. give information regarding whether it is PCP or elective or ICU. virtual or in person. within CHM or not
    just give infomartion on courses and no other advice 
    REMEMBER WHEN YOU GIVE INFORMATION ABOUT COURSE
    - Always mention course number and name
    - duration allowed
    - whether virtual or in person

    PLEASE DO NOT FORGET TO MENTION THE COURSE NUMBER AS IT IS FOR EVERY COURSE YOU MENTION
    """

    response = gemini.invoke(result)
    
    #print(response.text)

    if os.getenv("ENV") == "prod":
        res = response.content
    else:
        res = response.text

    return {

        "course_results":
        [res],

       
    }


def constraint_checker(state):

    errors=[]


    # Example rule

    weeks=[]

    for key,value in state["schedule"].items():

        if key.startswith("week"):

            if value["course"]:
                weeks.append(value["course"])



    if len(weeks) != len(set(weeks)):

        errors.append(
            "Duplicate course detected"
        )


    if errors:

        return {
            "task_results":
            state["task_results"]
            +
            errors
        }


    return {}

def response_agent(state):

    print("response")
    rag_context = retriever.invoke(state["user_message"])
    # for i,doc in enumerate(rag_context):
    #     print("=" * 80)
    #     print(f"RESULT {i + 1}")
    #     print(doc.page_content)
    #     print(doc.metadata)

   

    prompt=f"""

    You are an expert assistant helping domain experts who may not be expert programmers.

Your task is to answer the user's current question using:
1. The conversation history, which provides context about what the user is trying to accomplish.
2. The user's current question.
3. The retrieved RAG context, which contains relevant information from documentation, examples, or reference material.

Your goal is to provide a scientifically accurate, practical, and easy-to-understand answer.

IMPORTANT INSTRUCTIONS:

- Use the conversation history to understand the user's intent and avoid asking for information that has already been provided.
- Use the RAG context as the primary source for technical details when it is relevant.
- Do not blindly copy the RAG context. Explain it in your own words and adapt it to the user's question.
- If the RAG context contains R code relevant to the question, use it appropriately.
- If you provide R code, provide complete and executable R code whenever possible.
- Explain important parts of the code in terms that a domain expert can understand.
- Assume the user understands the scientific/domain concepts but may not be an expert R programmer.
- Do not invent functions, arguments, package behavior, or results that are not supported by the RAG context or established knowledge.
- If the information needed to answer the question is not available, clearly state what is missing rather than making up an answer.
- If there are multiple reasonable approaches, explain the recommended approach and briefly mention alternatives.
- Preserve important scientific terminology, variable names, and package names from the user's context.

R CODE FORMATTING REQUIREMENT:

Whenever you provide R code, you MUST enclose the entire R code block between these exact markers:

<!code start>
[ R code here ]
<!code end>

Do NOT use Markdown triple backticks for R code.

For example:

<!code start>
library(BGLR)

EVD <- eigen(G)

fm3 <- BGLR(
  y = y,
  ETA = list(
    G = list(
      V = EVD$vectors,
      d = EVD$values,
      model = "RKHS"
    )
  ),
  nIter = nIter,
  burnIn = burnIn
)
<!code end>

These markers must appear exactly as written:
<!code start>
<!code end>

If there are multiple separate R code sections, each one must have its own <!code start> and <!code end> markers.

Do not put explanations inside the code markers unless they are valid R comments.

CONVERSATION HISTORY:
{state["chat_history"]}

CURRENT USER QUESTION:
{state["user_message"]}

RETRIEVED RAG CONTEXT:
{rag_context}

Now answer the current user question.

            """
    
    


    answer=gemini.invoke(prompt)
    #print(answer)

    if os.getenv("ENV") == "prod":
            res = answer.content
    else:
        res = answer.text

    code_blocks = re.findall(
    r"<!code start>\s*(.*?)\s*<!code end>",
    res,
    re.DOTALL
    )

    

    html = ""

    for code in code_blocks:
        html += f"""
        <pre><code>{escape(code)}</code></pre>
        """

   

    # Remove code blocks
    res = re.sub(
        r"<!code start>.*?<!code end>",
        "",
        res,
        flags=re.DOTALL,
    ).strip()

    #print(res)

        

    


    return {
        "response":res,
        "code":html
    }

from langgraph.graph import StateGraph, START, END

graph_builder = StateGraph(SchedulerState)

# Nodes

graph_builder.add_node(
    "context_managaer",
    context_managaer
)


# graph_builder.add_node(
#     "recommend_agent",
#     recommend_agent
# )

# graph_builder.add_node(
#     "schedule_agent",
#     schedule_agent
# )

graph_builder.add_node(
    "response_agent",
    response_agent
)


# START → Context Agent
graph_builder.add_edge(
    START,
    "context_managaer"
)

# Context Agent → Intent Agent
graph_builder.add_edge(
    "context_managaer",
    "response_agent"
)

# Response → END
graph_builder.add_edge(
    "response_agent",
    END
)


app_lg = graph_builder.compile()

