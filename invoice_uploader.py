import boto3
import json
import base64
import logging
from kafka import KafkaConsumer
from datetime import datetime
from dotenv import load_dotenv
from db_access import InventoryValidator

# Load environment variables from .env file
load_dotenv()
import os

# AWS S3 Config
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
print(AWS_ACCESS_KEY)
METADATA_FILE = "metadata.json"

# Kafka Config
KAFKA_TOPIC = "email-invoices"
BOOTSTRAP_SERVERS = "localhost:9092"

# Set up logging
log_file_path = "invoice_uploader.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,  # Log only essential updates
    format="%(asctime)s %(levelname)s: %(message)s",
    filemode="w"
)

# Console logging (only for errors)
console = logging.StreamHandler()
console.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

logging.info("Invoice Processor Script Started.")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

def fetch_metadata():
    """Fetches the existing metadata.json from S3."""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=METADATA_FILE)
        return json.loads(response["Body"].read().decode("utf-8"))
    except s3_client.exceptions.NoSuchKey:
        return {"invoices": []}  # Create new metadata if missing
    except Exception as e:
        logging.error(f"Error fetching metadata.json: {e}")
        return {"invoices": []}

def upload_metadata(metadata):
    """Uploads updated metadata.json back to S3."""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=METADATA_FILE,
            Body=json.dumps(metadata, indent=4).encode("utf-8")
        )
    except Exception as e:
        logging.error(f"Error updating metadata.json: {e}")

def upload_to_s3(file_name, file_data):
    """Uploads the PDF to S3 and returns the file path."""
    year_month = datetime.now().strftime("%Y/%m")  # Format: 2025/03
    s3_key = f"raw/{year_month}/{file_name}"

    try:
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=file_data)
        return f"s3://{S3_BUCKET_NAME}/{s3_key}"
    except Exception as e:
        logging.error(f"Failed to upload {file_name} to S3: {e}")
        return None

def process_message(message):
    """Processes a Kafka message containing an email invoice."""
    try:
        data = message.value  # Already a dictionary, no need to decode

        email_id = data.get("email_id")
        sender = data.get("sender")

        metadata = fetch_metadata()

        # ✅ Check if the exact file (email_id + file_name) already exists
        processed_files = {(inv["email_id"], inv["file_name"]) for inv in metadata["invoices"]}

        new_entries = []  # Track newly added metadata entries

        for attachment in data.get("attachments", []):
            file_name = attachment["file_name"]

            # ✅ Skip processing if this email_id + file_name combination is already in metadata
            if (email_id, file_name) in processed_files:
                logging.info(f"Skipping {file_name} from email {email_id}: Already processed.")
                continue  # Skip this attachment

            file_data = base64.b64decode(attachment["file_data"])
            
            s3_path = upload_to_s3(file_name, file_data)
            if not s3_path:
                continue  # Skip if upload failed
            
            new_entry = {
                "email_id": email_id,
                "sender": sender,
                "received_at": datetime.utcnow().isoformat(),
                "file_name": file_name,
                "s3_path": s3_path,
                "status": "raw"
            }
            metadata["invoices"].append(new_entry)
            new_entries.append(new_entry)
            print(new_entry)
            validator = InventoryValidator()
            validator.insert_invoice_s3(new_entry)
            logging.info(f"Uploaded {file_name} to S3: {s3_path}")
            

        if new_entries:
            upload_metadata(metadata)  # ✅ Only update metadata if new invoices were added
            logging.info(f"Processed email {email_id} with {len(new_entries)} new attachment(s).")
    
    except Exception as e:
        logging.error(f"Error processing message: {e}")


def consume_kafka():
    """Consumes messages from Kafka and processes them."""
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            group_id="invoice_processor_group",
            auto_offset_reset="latest",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode("utf-8"))
        )

        logging.info("Kafka Consumer started, waiting for messages...")

        for message in consumer:
            process_message(message)
            consumer.commit()

    except Exception as e:
        logging.error(f"Kafka Consumer error: {e}")

if __name__ == "__main__":
    consume_kafka()
