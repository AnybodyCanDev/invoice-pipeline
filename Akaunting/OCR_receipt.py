import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import json
import sys
import os
import google.generativeai as genai
from validator import load_invoices

# Get the parent directory of the current script
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add parent directory to sys.path
sys.path.append(parent_dir)

# Configure Gemini API
API_KEY = "GEMINI_KEY"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

def ocr_file(file_path):
    """
    Extract text from a PDF or image file using PyMuPDF (for PDFs) and Tesseract OCR.
    """
    text = ""
    file_ext = file_path.lower().split(".")[-1]
    
    if file_ext in ["pdf"]:
        pdf_document = fitz.open(file_path)
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            page_text = page.get_text()
            
            if len(page_text.strip()) < 10:  # If no text, use OCR
                print(f"Using OCR for page {page_num + 1}...")
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Increase resolution
                img = Image.open(io.BytesIO(pix.tobytes()))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                page_text = pytesseract.image_to_string(img)
            
            text += f"\n\n--- Page {page_num + 1} ---\n\n" + page_text
    
    elif file_ext in ["png", "jpg", "jpeg", "tiff", "bmp", "gif"]:
        print("Processing image for OCR...")
        img = Image.open(file_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        text = pytesseract.image_to_string(img)
    
    else:
        raise ValueError("Unsupported file format. Please use PDF or an image file.")
    
    return text

def extract_warehouse_receipt(data):
    """
    Extract warehouse receipt number and items with quantities from text.
    """
    prompt = f"""
    You are a specialized AI assistant for extracting warehouse receipt data from text and converting it to a structured JSON format.
    
    Extract the Warehouse Receipt Number and the list of items with their quantities from the given text.
    Format the response STRICTLY as valid JSON without any additional text or explanations:
    [
        {{
            "zoho_po_number": "<Extracted Receipt Number>",
            "items": [
                {{ "description": "<Item 1>", "quantity": <Quantity> }},
                {{ "description": "<Item 2>", "quantity": <Quantity> }}
            ]
        }}
    ]
    
    Text:
    {data}
    
    IMPORTANT: Return ONLY the JSON object without any surrounding text, markdown formatting, or explanation.
    """
    
    # Generate the response from the model
    response = model.generate_content(prompt)
    
    # Print the response for debugging
    print(f"Response: {response.text}")
    
    try:
        # Sometimes the response might include markdown code blocks or other formatting
        response_text = response.text.strip()
        
        # Check if the response is wrapped in markdown code blocks
        if response_text.startswith("```json") and response_text.endswith("```"):
            json_content = response_text[7:-3].strip()  # Remove ```json and ```
        elif response_text.startswith("```") and response_text.endswith("```"):
            json_content = response_text[3:-3].strip()  # Remove ``` and ```
        else:
            json_content = response_text
        
        receipt_json = json.loads(json_content)
        return receipt_json
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw response: {response.text}")
        
        # Return a fallback structure if parsing fails
        return [{
            "zoho_po_number": "ERROR_PARSING_RECEIPT",
            "items": [
                {"description": "Error extracting data", "quantity": 0}
            ]
        }]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ No PDF file provided. Exiting.")
        sys.exit(1)

    pdf_file = sys.argv[1]
    # pdf_file = "/Users/kriti.bharadwaj03/digitalInvoiceProcessing/Akaunting/invoices/Invoice_img.jpeg"
    
    # Optional: Extract email_id if provided
    email_id = sys.argv[2] if len(sys.argv) > 2 else None

    # Create output directory if it doesn't exist
    os.makedirs("Akaunting/data", exist_ok=True)

    # Process the PDF
    extracted_text = ocr_file(pdf_file)
    structured_data = extract_warehouse_receipt(extracted_text)

    # Save the structured data
    with open("Akaunting/data/receipts.json", "w") as json_file:
        json.dump(structured_data, json_file, indent=4)

    print("✅ Extracted and saved warehouse receipt data successfully.")
