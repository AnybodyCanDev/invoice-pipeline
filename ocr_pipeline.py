import json
import os
import logging
import base64
from kafka import KafkaConsumer
from datetime import datetime
import subprocess

# Local file to track processed emails
PROCESSED_EMAILS_FILE = "processed_emails.json"

# Kafka Config
KAFKA_TOPIC = "ocr"
BOOTSTRAP_SERVERS = "localhost:9092"
INVOICE_DIR = "Akaunting/invoices"

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

def run_main_py():
    """Run the main.py script."""
    try:
        subprocess.run(["python3", "/Users/kriti.bharadwaj03/digitalInvoiceProcessing/Akaunting/main.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running main.py: {e}")
# ✅ Load processed emails from the local JSON file
def load_processed_emails():
    if not os.path.exists(PROCESSED_EMAILS_FILE):
        return set()  # Return empty set if file does not exist
    try:
        with open(PROCESSED_EMAILS_FILE, "r") as f:
            return set(json.load(f))  # Load as set for fast lookups
    except Exception as e:
        logging.error(f"Error loading processed emails: {e}")
        return set()

# ✅ Save processed emails back to the local JSON file
def save_processed_email(email_id):
    processed_emails = load_processed_emails()
    processed_emails.add(email_id)  # Add new email ID
    try:
        with open(PROCESSED_EMAILS_FILE, "w") as f:
            json.dump(list(processed_emails), f, indent=4)  # Convert set to list
    except Exception as e:
        logging.error(f"Error saving processed email {email_id}: {e}")

def process_message(message):
    """Processes a Kafka message containing an email invoice."""
    try:
        data = message.value
        email_id = data.get("email_id")
        
        if not email_id:
            logging.error("Received message without email_id, skipping...")
            return

        processed_emails = load_processed_emails()

        # ✅ Skip processing if email was already handled
        if email_id in processed_emails:
            print(f"⏩ Skipping email {email_id}: Already processed for OCR.")  # 🔹 Added print
            logging.info(f"Skipping email {email_id}: Already processed for OCR.")
            return

        # Simulate OCR processing for each attachment
        for attachment in data.get("attachments", []):
            file_name = attachment["file_name"]
            file_data = base64.b64decode(attachment["file_data"])
            file_data = base64.b64decode(attachment["file_data"])
            
            file_path = os.path.join(INVOICE_DIR, file_name)

            with open(file_path, "wb") as f:
                f.write(file_data)

            logging.info(f"✅ Saved invoice {file_name} from email {email_id} to {file_path}")
            
            # Run main.py with the saved file
            logging.info(f"🚀 Running main.py with {file_path}")
            subprocess.run(["python", "/Users/kriti.bharadwaj03/digitalInvoiceProcessing/Akaunting/main.py", file_path, email_id])

            # print(f"✅ Processing invoice: {file_name} from email {email_id}")  # 🔹 Added print
            # logging.info(f"Performing OCR on {file_name} from email {email_id}...")
            # ⏳ Call your OCR function here

        # ✅ Mark email as processed only after successful OCR
        save_processed_email(email_id)
        logging.info(f"OCR processing complete for email {email_id}.")

    except Exception as e:
        logging.error(f"Error processing email {email_id if 'email_id' in locals() else 'UNKNOWN'}: {e}")

def consume_kafka():
    """Consumes messages from Kafka and processes them."""
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            group_id="ocr_processor_group",
            auto_offset_reset="latest",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode("utf-8"))
        )

        logging.info("OCR Kafka Consumer started, waiting for messages...")

        for message in consumer:
            process_message(message)
            consumer.commit()

    except Exception as e:
        logging.error(f"Kafka Consumer error: {e}")

if __name__ == "__main__":
    consume_kafka()
