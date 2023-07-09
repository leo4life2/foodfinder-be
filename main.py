from yelp import get_nearby_food_info
from tokenizer import num_tokens_from_string
from llm import LLM
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from enum import Enum
from typing import List
from langchain.schema import AIMessage, HumanMessage, SystemMessage
import json

class MessageType(str, Enum):
    system = "system"
    ai = "ai"
    user = "user"

class Message(BaseModel):
    role: MessageType
    content: str

class FoodRequest(BaseModel):
    address: str
    is_first: bool
    messages: List[Message]

app = FastAPI()

origins = [
    "http://localhost:3000",  # React
    "http://localhost:8000",  # Vue.js
    "http://localhost:8080",  # Angular
    "https://foodfinder-fe.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def langchain_messages_to_json(messages):
    json = []
    for m in messages:
        if isinstance(m, SystemMessage):
            json.append(Message(role=MessageType.system, content=m.content))
        elif isinstance(m, AIMessage):
            json.append(Message(role=MessageType.ai, content=m.content))
        elif isinstance(m, HumanMessage):
            json.append(Message(role=MessageType.user, content=m.content))
    return json

@app.get("/")
async def root():
    print("This is the root endpoint.")
    return {"message": "Hello World"}        

@app.post("/ask")
async def ask(request: FoodRequest):    
    if request.is_first:
        print("Is first!")
        # If this is the first message, get the restaurant info, and put that in the system prompt, and have the system prompt as the first message.
        messages = []
        
        address = request.address
        nearby_food_info, food_info_json = get_nearby_food_info(address, term="food", radius=2000, sort_by="best_match", limit=25)
        
        print("Food info tokens:", num_tokens_from_string(nearby_food_info))
        prompt = open('system_prompt.txt', 'r').read()
        prompt += nearby_food_info
        # with open('complete_prompt.txt', 'w') as outfile:
        #     outfile.write(prompt)
        # with open('food_info.json', 'w') as outfile:
        #     outfile.write(json.dumps(food_info_json))
            
        messages.append(SystemMessage(content=prompt))
        # Then, we have the user's prompt as the second message.
        messages.append(HumanMessage(content=request.messages[0].content))
        
        llm = LLM()
        response = llm.ask(messages)
        print("response is", response)
        
        return {
            "response": response.content,
            "system_prompt": prompt,
            "food_info": food_info_json
        }
        
    else:
        # Process the messages into langchain schema.
        print("Not first!")
        print("history is", request.messages)
        
        messages = []
        for m in request.messages:
            if m.role == MessageType.system:
                messages.append(SystemMessage(content=m.content))
            elif m.role == MessageType.ai:
                messages.append(AIMessage(content=m.content))
            elif m.role == MessageType.user:
                messages.append(HumanMessage(content=m.content))
                
        llm = LLM()
        response = llm.ask(messages)
        
        print("response is", response)
        
        return {
            "response": response.content
        }
