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

from src.main import process_pdf
from src.config import MODEL, SYSTEM_PROMPT


def clean_and_parse_json(raw_content: str) -> dict:
    """Extracts the first valid JSON object from a string."""
    json_start_index = raw_content.find('{')
    json_end_index = raw_content.rfind('}')
    if json_start_index == -1 or json_end_index == -1:
        raise ValueError("No valid JSON object found in the model's response.")
    json_string = raw_content[json_start_index : json_end_index + 1]
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to decode JSON. Error: {e}. Content: {json_string}")

def format_json_display(json_data: dict) -> str:
    """Formats JSON data into a clean, readable HTML view (this part remains light-themed)."""
    if not isinstance(json_data, dict) or not json_data:
        return "<div class='invoice-container no-data'>Awaiting Invoice Data...</div>"
    
    def fnum(n, precision=2):
        return f"{n:.{precision}f}" if isinstance(n, (int, float)) else ""

    html = "<div class='invoice-container'>" # Main container for the light-mode island
    html += f"<h1>Invoice</h1><p class='generation-date'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"

    html += "<div class='grid-container'>"
    html += f"<div class='grid-item'><h3>Billed To</h3><p><strong>{json_data.get('customer_name', 'N/A')}</strong></p><p>{json_data.get('customer_address', '')}</p></div>"
    html += f"<div class='grid-item'><h3>From</h3><p><strong>{json_data.get('vendor_name', 'N/A')}</strong></p><p>{json_data.get('vendor_address', '')}</p></div>"
    html += "</div>"
    
    html += "<div class='details-grid'>"
    html += f"<p><strong>Invoice #:</strong> {json_data.get('invoice_number', 'N/A')}</p>"
    html += f"<p><strong>Date:</strong> {json_data.get('invoice_date', 'N/A')}</p>"
    html += "</div>"
    
    if json_data.get('line_items'):
        html += "<h3>Line Items</h3><table class='styled-table'><thead><tr><th>Description</th><th>Qty</th><th>Unit Price</th><th>Total</th></tr></thead><tbody>"
        for item in json_data.get('line_items', []):
            qty = item.get('quantity')
            price = item.get('unit_price')
            total = (qty * price) if qty is not None and price is not None else 0
            html += f"<tr><td>{item.get('description', '')}</td><td>{qty if qty is not None else ''}</td><td>{fnum(price)}</td><td>{fnum(total)}</td></tr>"
        html += "</tbody></table>"
        
    html += "<div class='summary-box'>"
    html += f"<div><span>Subtotal</span><span>{fnum(json_data.get('subtotal'))}</span></div>"
    html += f"<div><span>Tax</span><span>{fnum(json_data.get('tax'))}</span></div>"
    html += f"<div class='total'><span>Total ({json_data.get('currency', '')})</span><span>{fnum(json_data.get('total_amount'))}</span></div>"
    html += "</div></div>"
    return html

def initial_process_pdf(pdf_file, progress=gr.Progress()):
    """Phase 1: Processes PDF, gets initial JSON, returns data and makes UI visible."""
    if pdf_file is None:
        return None, [], None, gr.update(visible=False), format_json_display({})
    
    try:
        structured_data = process_pdf(pdf_file, progress)
        formatted_display = format_json_display(structured_data)
        progress(1, desc="Parsing complete!")
        initial_chatbot_message = [(None, "I've analyzed the document. You can now ask me to refine or query the results.")]
        return structured_data, [], initial_chatbot_message, gr.update(visible=True), formatted_display
    
    except Exception as e:
        raise gr.Error(f"Failed to call Ollama or parse its response: {e}")

def handle_chat_message(user_message: str, chat_history: list, image_paths: list, current_json: dict):
    if not image_paths:
        chat_history.append((user_message, "Error: No document context. Please upload a PDF first."))
        return "", chat_history, format_json_display(current_json), current_json

    chat_history.append((user_message, None))
    chat_prompt = f"""You are a helpful assistant analyzing an invoice. You have already extracted this JSON:
--- INITIAL JSON ---
{json.dumps(current_json, indent=2)}
--- END INITIAL JSON ---
The user has a follow-up question. Based on the attached invoice image(s) and the initial JSON, provide a concise answer.
IMPORTANT: If the user asks you to change, correct, or update the data, you MUST provide the complete, updated JSON structure within a ```json ... ``` code block in your response.

User's question: "{user_message}"
"""
    try:
        response = ollama.chat(model=MODEL, messages=[{'role': 'user', 'content': chat_prompt, 'images': image_paths}])
        assistant_response = response['message']['content']
        chat_history[-1] = (user_message, assistant_response)
        
        try:
            updated_json_data = clean_and_parse_json(assistant_response)
            print("Chat updated the JSON.")
            return "", chat_history, format_json_display(updated_json_data), updated_json_data
        except (ValueError, json.JSONDecodeError):
            return "", chat_history, format_json_display(current_json), current_json
    except Exception as e:
        chat_history[-1] = (user_message, f"Sorry, an error occurred: {e}")
        return "", chat_history, format_json_display(current_json), current_json


night_mode_css = """
/* Overall Dark Theme */
body, .gradio-container { background-color: #0d1117; color: #c9d1d9; }
.main-column { gap: 2rem !important; }
.dark-group { background-color: #161b22; border: 1px solid #30363d !important; border-radius: 8px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.dark-group h3, .dark-group .gr-markdown p { color: #c9d1d9; }
.gr-button { background-color: #238636 !important; color: white !important; }

/* The Light-Mode Island for Formatted View */
.invoice-container { background: white !important; color: #1a1a1a !important; padding: 25px; border-radius: 8px; font-family: 'Segoe UI', Tahoma, sans-serif; }
.invoice-container h1 { color: #1a1a1a !important; text-align: center; margin-bottom: 5px;}
.invoice-container h3 { color: #3a3a3a !important; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 20px; }
.invoice-container .generation-date { text-align: center; color: #6a737d; margin-bottom: 30px; font-size: 0.9em; }
.invoice-container .grid-container { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-bottom: 25px; }
.invoice-container .grid-item p { margin: 4px 0; color: #3a3a3a !important; }
.invoice-container .details-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; background: #f6f8fa; padding: 15px; border-radius: 6px; margin-bottom: 20px;}
.invoice-container .details-grid p { margin: 4px 0; color: #3a3a3a !important;}
.invoice-container .styled-table { width: 100%; border-collapse: collapse; margin-top: 15px; }
.invoice-container .styled-table th, .invoice-container .styled-table td { border: 1px solid #e2e8f0; padding: 12px; text-align: left; color: #1a1a1a !important; }
.invoice-container .styled-table th { background-color: #f6f8fa; font-weight: 600; }
.invoice-container .summary-box { margin-top: 25px; padding-top: 15px; border-top: 2px solid #e2e8f0; }
.invoice-container .summary-box div { display: flex; justify-content: space-between; padding: 6px 0; font-size: 1.1em; }
.invoice-container .summary-box .total { font-weight: bold; font-size: 1.3em; color: #1a1a1a !important; border-top: 2px solid #000; margin-top: 10px; padding-top: 10px;}
.invoice-container .no-data { text-align: center; padding: 40px; color: #718096 !important; }
.invoice-container strong,
.invoice-container b { color: #1a1a1a !important; }
.invoice-container .summary-box span {
    color: #30302E !important;
}

"""

with gr.Blocks(theme=gr.themes.Base(), css=night_mode_css, title="Interactive Invoice Parser") as demo:
    image_paths_state = gr.State([])
    json_state = gr.State({})

    with gr.Column(elem_classes="main-column"):
        gr.Markdown(f"# 📄 Interactive Invoice Parser\nUpload a PDF to start a conversation with **{MODEL}**.")
        
        with gr.Group(elem_classes="dark-group"):
            pdf_upload = gr.File(label="Upload PDF Invoice", file_types=[".pdf"])
            process_button = gr.Button("🚀 Process Invoice", variant="primary")

        with gr.Row(visible=False, elem_classes="results-chat-area") as results_and_chat_area:
            with gr.Column(scale=2, elem_classes="view-column dark-group"):
                gr.Markdown("### 📊 Extracted Data")
                with gr.Tabs():
                    with gr.TabItem("📋 Formatted View"):
                        formatted_output = gr.HTML()
                    with gr.TabItem("🔧 Raw JSON"):
                        json_output_raw = gr.JSON()

            with gr.Column(scale=1, elem_classes="chat-column dark-group"):
                gr.Markdown("### 💬 Interactive Chat")
                chatbot = gr.Chatbot(height=500, bubble_full_width=False, avatar_images=("./user.png", "./bot.png"))
                chat_textbox = gr.Textbox(placeholder="e.g., Change the vendor name...", show_label=False)

    def process_pdf_and_update_ui(pdf_file, progress=gr.Progress()):
        total_wait_time = 32  # seconds
        steps = 4  # number of progress updates
        step_duration = total_wait_time / steps
    
        for i in range(steps):
            progress(i / steps, desc=f"Processing... {int((i / steps) * 100)}%")
            time.sleep(step_duration)
    
        # Actual processing starts after simulated wait
        json_data, image_paths, initial_chat, visibility_update, formatted_html = initial_process_pdf(pdf_file, progress)
        return json_data, image_paths, initial_chat, visibility_update, formatted_html, json_data
    
    process_button.click(
        fn=process_pdf_and_update_ui,
        inputs=[pdf_upload],
        outputs=[json_state, image_paths_state, chatbot, results_and_chat_area, formatted_output, json_output_raw]
    )

    def chat_and_update_ui(msg, history, paths, current_json):
        msg_out, updated_history, updated_html, updated_json = handle_chat_message(msg, history, paths, current_json)
        return msg_out, updated_history, updated_html, updated_json, updated_json

    chat_textbox.submit(
        fn=chat_and_update_ui,
        inputs=[chat_textbox, chatbot, image_paths_state, json_state],
        outputs=[chat_textbox, chatbot, formatted_output, json_state, json_output_raw]
    )
    
    def clear_all_ui():
        return None, gr.update(visible=False), None, format_json_display({}), {}, []

    pdf_upload.clear(
        fn=clear_all_ui,
        inputs=[],
        outputs=[pdf_upload, results_and_chat_area, chatbot, formatted_output, json_state, image_paths_state]
    )


if __name__ == "__main__":
    print(f"Launching Gradio App with model: {MODEL}")
    demo.launch()
