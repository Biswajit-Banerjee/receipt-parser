import gradio as gr
import ollama
import pypdf
import os
import json
import re
from PIL import Image
from pdf2image import convert_from_path
import tempfile
import shutil
from datetime import datetime 
import time
from pprint import pprint

from config import MODEL, SYSTEM_PROMPT

def clean_and_parse_json(raw_content: str) -> dict:
    # Remove potential markdown code blocks
    cleaned_content = re.sub(r" ```json\n?", "", raw_content)
    cleaned_content = re.sub(r" ```", "", cleaned_content)
    cleaned_content = cleaned_content.strip()  
    
    # Find the start of the JSON object
    json_start_index = cleaned_content.find('{')
    json_end_index   = cleaned_content.rfind('}')
    if json_start_index == -1:
        raise json.JSONDecodeError("No JSON object found in the model's response.", cleaned_content, 0)

    # Extract the JSON part of the string
    json_string = cleaned_content[json_start_index:json_end_index+1]
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Failed to decode JSON: {e}", cleaned_content, e.pos)


def extract_text_from_pdf(pdf_path: str) -> str:
    if not os.path.exists(pdf_path):
        return ""
    try:
        reader = pypdf.PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    
    except Exception as e:
        print(f"Warning: Could not extract text from PDF. Error: {e}")
        return ""
    
    
def execute_prompt(messages: list, model: str=MODEL, system_prompt: str=SYSTEM_PROMPT):
    
    try:
        # Call Ollama, providing both the text prompt and the list of image paths
        response = ollama.chat(
            model=model,
            messages=messages
        )
        
        # The response content might be a string or already a dict depending on the model/Ollama version
        raw_content = response['message']['content'] if isinstance(response['message']['content'], str) else json.dumps(response['message']['content'])
        
        return raw_content
        
    except Exception as e:
        return {"error": f"Failed to call Ollama or parse its response: {e}"}
