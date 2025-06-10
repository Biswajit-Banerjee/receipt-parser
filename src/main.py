from pdf2image import convert_from_path
import gradio as gr
import json
import os 
from .config import SYSTEM_PROMPT, MOCK_DATABASE
from .invoice_processor import extract_text_from_pdf, clean_and_parse_json, execute_prompt


def pdf_to_images(pdf_path, temp_dir):
    image_paths = []
    
    images = convert_from_path(pdf_path)
    
    # Save each image to the temporary directory and collect their paths
    for i, img in enumerate(images):
        image_path = os.path.join(temp_dir, f"page_{i+1}.png")
        img.save(image_path)
        image_paths.append(image_path)
            
    return image_paths

def query_rag(image_paths, query_text=None):

    db_string = json.dumps(MOCK_DATABASE, indent=2)

    system_prompt = f"""
    You are a specialized entity resolution system. 
    Your sole task is to analyze a user's query, which may come from text or an image, and find the corresponding official entity in the provided JSON database.
    Keep in mind, this is very mission critical, you have to carefully evaluate the match, and there might be no matches so be prepared for that. 

    **Database of Known Entities:**
    ```json
    {db_string}
    ```

    **Your Instructions:**

    1.  **Analyze the Query**: The user will provide a name or a document. Extract the most likely name of the organization they are referring to.
    2.  **Search the Database**: Compare the extracted name against the "canonical_name" and "aliases" fields in the database. The match might not be perfect, so find the most plausible entry.
    3.  **Format the Output**: You MUST respond with a single JSON object.

        * **If a match is found**, the JSON object should contain:
            - "status": "FOUND"
            - "Confidante": float confidante value
            - "id": The unique ID of the matched entity (e.g., "111-JKL").
            - "canonical_name": The official name from the database.
            - "searched_term": The term you extracted from the user's query.

        * **If no match is found**, the JSON object should contain:
            - "status": "NOT_FOUND"
            - "searched_term": The term you extracted but could not match.

    **IMPORTANT**: Use ONLY the information in the provided database. Do not use your own knowledge about any companies. Your entire world is the database above.
    This is very critical, you have to match and align properly or return NOT_FOUND.
    """
    user_content = query_text if query_text else "Please identify the vendor in the attached image from internal database, if not found return not found."
    
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_content, 'images': image_paths}
    ]
    
    return execute_prompt(messages)
    
def process_pdf(pdf_file, progress=None):
    if progress is None:
        progress = gr.Progress()
    
    # Use a temporary directory that automatically cleans up after itself
    temp_dir = os.path.join("temp", os.path.basename(pdf_file)[:-4])
    os.makedirs(temp_dir, exist_ok=True)
    
    progress(0.1, desc="Extracting images from PDFs...")
    image_paths = pdf_to_images(pdf_file, temp_dir)
    invoice_text = extract_text_from_pdf(pdf_file)
    
    progress(0.4, desc="Querying RAG to fetch vendor information...")
    retrieved_vendor_info = query_rag(image_paths)
    
    parsing_query = "\n".join([
        f"You are processing an invoice.",
        "Using our internal database, we have verified the vendor information, always use canonical name if available. Here is the official data for this vendor (ignore if empty):",
        f"--- VERIFIED VENDOR DATA ---\n{retrieved_vendor_info}\n--- END VERIFIED VENDOR DATA ---",
        "The following is text extracted directly from the PDF, which you can use as context to improve accuracy:",
        f"--- EXTRACTED TEXT ---\n{invoice_text}\n--- END TEXT ---",
        "Now, using this verified data as the ground truth for the vendor, Analyze the attached invoice image(s) and extract all information as per the system prompt's JSON structure."
    ])
    
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': parsing_query, 'images': image_paths}
    ]
    
    progress(0.7, desc="Parsing the document...")
    raw_content = execute_prompt(messages)
    
    structured_data = clean_and_parse_json(raw_content)

    return structured_data, image_paths


if __name__ == "__main__":
    from pprint import pprint 
    
    pdf_path = "/home/sumon/workspace/git_repos/receipt-parser/temp/batch1-0001.pdf"
    pprint(process_pdf(pdf_path))
    