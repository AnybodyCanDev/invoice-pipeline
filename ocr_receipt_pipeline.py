import json
import os
import logging
import base64
from kafka import KafkaConsumer
from datetime import datetime
import subprocess

# # Local file to track processed emails
PROCESSED_EMAILS_FILE = "grn_processed_emails.json"
# In your Kafka consumer script, change this line:
RECEIPTS_JSON_FILE = "Akaunting/data/receipts.json"  # Match the path in OCR_receipt.py
# Kafka Config
KAFKA_TOPIC = "ocr_grn"
BOOTSTRAP_SERVERS = "localhost:9092"
RECEIPT_DIR = "Akaunting/receipts"

# Set up logging
logging.basicConfig(
    filename="ocr_pipeline.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    filemode="w"
)

# Console logging (only for errors)
console = logging.StreamHandler()
console.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

# ✅ Ensure receipt directory exists
os.makedirs(RECEIPT_DIR, exist_ok=True)

def run_ocr_extraction(pdf_file):
    """Run OCR_PDF.py with the provided PDF file path."""
    print(f"🔍 Running OCR extraction on: {pdf_file}")
    try:
        # Change this line
        subprocess.run(["python", "/Users/kriti.bharadwaj03/digitalInvoiceProcessing/Akaunting/OCR_receipt.py", pdf_file])    
        
    except subprocess.CalledProcessError as e:
        print(f"❌ OCR extraction failed: {e}")
        sys.exit(1)

def load_processed_emails():
    """Load processed emails from local JSON file."""
    if not os.path.exists(PROCESSED_EMAILS_FILE):
        return set()
    try:
        with open(PROCESSED_EMAILS_FILE, "r") as f:
            return set(json.load(f))
    except Exception as e:
        logging.error(f"Error loading processed emails: {e}")
        return set()

def save_processed_email(email_id):
    """Save processed email ID to prevent duplicate processing."""
    processed_emails = load_processed_emails()
    processed_emails.add(email_id)
    try:
        with open(PROCESSED_EMAILS_FILE, "w") as f:
            json.dump(list(processed_emails), f, indent=4)
    except Exception as e:
        logging.error(f"Error saving processed email {email_id}: {e}")

def process_message(message):
    """Processes a Kafka message containing a receipt PDF."""
    try:
        data = message.value
        email_id = data.get("email_id")

        if not email_id:
            logging.error("Received message without email_id, skipping...")
            return

        # processed_emails = load_processed_emails()

        # if email_id in processed_emails:
        #     logging.info(f"Skipping email {email_id}: Already processed for OCR.")
        #     return

        receipts_data = []

        for attachment in data.get("attachments", []):
            file_name = attachment["file_name"]
            file_data = base64.b64decode(attachment["file_data"])

            # Save receipt PDF
            file_path = os.path.join(RECEIPT_DIR, file_name)
            with open(file_path, "wb") as f:
                f.write(file_data)

            logging.info(f"✅ Saved receipt {file_name} from email {email_id} to {file_path}")
            # Run main.py with the saved file
            logging.info(f"🚀 Running main.py with {file_path}")
            run_ocr_extraction(file_path)
            # receipt_entry = {
            #     "email_id": email_id,
            #     "file_name": file_name,
            #     "file_path": file_path,
            #     "timestamp": datetime.now().isoformat()
            # }
            # receipts_data.append(receipt_entry)

        # ✅ Store receipt details in receipts.json
        if receipts_data:
            if os.path.exists(RECEIPTS_JSON_FILE):
                with open(RECEIPTS_JSON_FILE, "r") as f:
                    existing_data = json.load(f)
            else:
                existing_data = []

            existing_data.extend(receipts_data)

            with open(RECEIPTS_JSON_FILE, "w") as f:
                json.dump(existing_data, f, indent=4)

            logging.info(f"📝 Receipt details stored in {RECEIPTS_JSON_FILE}")
        
        subprocess.run(["python", "/Users/kriti.bharadwaj03/digitalInvoiceProcessing/lakshya_validator.py"])
        # ✅ Mark email as processed
        save_processed_email(email_id)

    except Exception as e:
        logging.error(f"Error processing email {email_id if 'email_id' in locals() else 'UNKNOWN'}: {e}")

def consume_kafka():
    """Consumes messages from Kafka and processes receipts."""
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            group_id="receipt_processor_group",
            auto_offset_reset="latest",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode("utf-8"))
        )

        logging.info("🟢 Receipt Kafka Consumer started, waiting for messages...")

        for message in consumer:
            process_message(message)
            consumer.commit()

    except Exception as e:
        logging.error(f"Kafka Consumer error: {e}")

if __name__ == "__main__":
    consume_kafka()
