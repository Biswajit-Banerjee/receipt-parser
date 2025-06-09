
MODEL = "qwen2.5vl:7b"
EMBEDDING_MODEL = "nomic-embed-text"

SYSTEM_PROMPT = """
You are an expert at processing invoices. Your task is to extract information from the
invoice text provided and return it ONLY as a valid JSON object. Do not add any
introductory text, explanations, or markdown formatting around the JSON.

The required JSON structure is, make sure to ignore any filed which is not available, for those the content should be empty string:
{
    "invoice_number": "string",  
    "invoice_date": "string",
    "vendor_name": "string",
    "vendor_id": "string",
    "vendor_address": "string",
    "customer_name": "string",
    "customer_address": "string",
    "currency": "string",
    "line_items": [
        {
        "description": "string",
        "quantity": "integer",
        "unit_price": "float"
        }
    ],
    "subtotal": "float",
    "tax": "float",
    "total_amount": "float"
}
"""

MOCK_DATABASE = {
    "123-ABC": {
        "canonical_name": "XPO Logistics, Inc.",
        "aliases": ["XPO Logistics", "RXO Logistics"]
    },
    "456-DEF": {
        "canonical_name": "Kirby and Partners LLC",
        "aliases": ["Kirby and Valdez", "K&V"]
    },
    "789-GHI": {
        "canonical_name": "Stellapps",
        "aliases": ["Stellapps Technologies", "Stellapps Technologies pvt. ltd."] 
    },
    "111-JKL": {
        "canonical_name": "Georgia Institute of Technology",
        "aliases": ["GeorgiaTech", "GT", "GaTech"] 
    }   
}