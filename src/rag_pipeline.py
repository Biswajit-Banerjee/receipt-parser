import json
from .config import MOCK_DATABASE
from .invoice_processor import execute_prompt


def query_rag(image_paths, query_text=None):

    db_string = json.dumps(MOCK_DATABASE, indent=2)

    system_prompt = f"""
    You are a specialized entity resolution system. Your sole task is to analyze a user's query, which may come from text or an image, and find the corresponding official entity in the provided JSON database.

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
            - "id": The unique ID of the matched entity (e.g., "111-JKL").
            - "canonical_name": The official name from the database.
            - "searched_term": The term you extracted from the user's query.

        * **If no match is found**, the JSON object should contain:
            - "status": "NOT_FOUND"
            - "searched_term": The term you extracted but could not match.

    **IMPORTANT**: Use ONLY the information in the provided database. Do not use your own knowledge about any companies. Your entire world is the database above.
    """

    # The user's message is now just the raw input.
    # The detailed instructions are all in the system prompt.
    user_content = query_text if query_text else "Please identify the vendor in the attached image."
    
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_content, 'images': image_paths}
    ]
    
    return execute_prompt(messages)
    