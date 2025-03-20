import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import google.generativeai as genai
import json
import sys
import os
from validator import load_invoices
# Get the parent directory of the current script
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add parent directory to sys.path
sys.path.append(parent_dir)

# Now import db_access
from db_access import InventoryValidator

def ocr_pdf(pdf_path, output_text_file="extracted_text.txt"):
    """
    Extract text from a scanned PDF using PyMuPDF and Tesseract OCR.
    No Poppler required.
    """
    text = ""
    pdf_document = fitz.open(pdf_path)

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]

        # Try extracting text directly (if it's a normal PDF with selectable text)
        page_text = page.get_text()

        # If no text is found, use OCR
        if len(page_text.strip()) < 10:
            print(f"Using OCR for page {page_num + 1}...")

            # Convert the page to an image
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # Increase resolution
            img = Image.open(io.BytesIO(pix.tobytes()))

            # Convert to RGB mode if needed
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Perform OCR
            page_text = pytesseract.image_to_string(img)

        text += f"\n\n--- Page {page_num + 1} ---\n\n" + page_text
    return text


def format_with_gemini(data):
    # Define the prompt for invoice extraction
    prompt = """
You are a specialized AI assistant for extracting invoice data from text and converting it to a structured JSON format.

I'll provide the text extracted from an invoice. Please extract the following information and format it as JSON:
- Vendor name (company issuing the invoice)
- Bill/invoice number
- Bill/invoice date
- Due date or payment terms
- Bill-to information (name and address)
- Ship-to information (address)
- Line items (including item details, quantity, rate, and amount)
- Subtotal
- Tax information (rate and calculated amount)
- Total amount
- Any notes or terms

The text from the invoice is as follows:

""" + data + """

Please return the data in this exact JSON structure:
{
  "invoices": [
    {
      "vendor_name": "",
      "bill_number": "",
      "bill_date": "",
      "due_date": "",
      "items": [
        {
          "item_details": "",
          "account": "",
          "quantity": 0,
          "rate": 0,
          "amount": 0
        }
      ],
      "sub_total": 0,
      "discount": {
        "percentage": 0,
        "amount": 0
      },
      "tax": {
        "tds_percent": "0",
        "tds_amount": 0,
        "tds_tax_name": ""
      },
      "total": 0
    }
  ]
}

Don't include any explanations or markdown in your response, just the clean JSON output.
    """

    # Generate the response from the model
    response = model.generate_content(prompt)

    # Print the response from Gemini
    print(f"Response: {response.text}")

    invoicejsontext = response.text[8:-4]
    invoicejson = json.loads(invoicejsontext)

    # Save it to a file
    with open("Akaunting/data/invoices.json", "w") as json_file:
        json.dump(invoicejson, json_file, indent=4)  # Pretty format with indentation

    print("Saved JSON successfully!")
    validator = InventoryValidator()
    validator.test_connection()
    invoice_data = load_invoices()
    print(f"Loaded invoice data: {type(invoice_data)} -> {invoice_data}")  # Debugging

    if invoice_data:  # Ensure there is data before inserting
        validator.insert_invoice({"invoices": invoice_data},email_id)  # Pass as dict
        bill_number = invoice_data[0]["bill_number"]
        bill_number = bill_number[3:]
        validator.log_to_system('invoice',bill_number,{},'data extracted')
    else:
        log_info("No invoices found to insert.")
    
    


if __name__ == "__main__":
    if len(sys.argv) < 3:
          print("❌ No PDF file provided. Exiting.")
          sys.exit(1)

    pdf_file = sys.argv[1] 
    email_id = sys.argv[2]
      # Example Usage
    API_KEY = "AIzaSyArPDGh4zx22TN-uZ3kIo3KC4SrgF4_C4s"  # Replace with your actual key
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-1.5-pro-latest")
    # pdf_file = "Akaunting/invoices/INV_DUNDER_MIFFLIN_2.pdf"  # Replace with your PDF file path
    text = ocr_pdf(pdf_file)
    format_with_gemini(text)
    print("Saved in a JSON file.")

