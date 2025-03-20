import boto3
import json
import base64
import logging
from kafka import KafkaConsumer
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# AWS S3 Config
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Metadata file for GRNs
METADATA_FILE_GRN = "metadata_grn.json"

# Kafka Config
KAFKA_TOPIC_GRN = "grn"  # New topic for GRN files
BOOTSTRAP_SERVERS = "localhost:9092"

# Logging Setup
log_file_path = "grn_uploader.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    filemode="w"
)

console = logging.StreamHandler()
console.setLevel(logging.ERROR)
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

logging.info("GRN Processor Script Started.")

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

def fetch_metadata():
    """Fetches the existing metadata_grn.json from S3."""
    try:
        response = s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=METADATA_FILE_GRN)
        return json.loads(response["Body"].read().decode("utf-8"))
    except s3_client.exceptions.NoSuchKey:
        return {"grns": []}  # Create new metadata if missing
    except Exception as e:
        logging.error(f"Error fetching {METADATA_FILE_GRN}: {e}")
        return {"grns": []}

def upload_metadata(metadata):
    """Uploads updated metadata_grn.json back to S3."""
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=METADATA_FILE_GRN,
            Body=json.dumps(metadata, indent=4).encode("utf-8")
        )
    except Exception as e:
        logging.error(f"Error updating {METADATA_FILE_GRN}: {e}")

def upload_to_s3(file_name, file_data):
    """Uploads the GRN PDF to S3 and returns the file path."""
    year_month = datetime.now().strftime("%Y/%m")  # Format: 2025/03
    s3_key = f"grn/{year_month}/{file_name}"  # Store under "grn/"

    try:
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=file_data)
        return f"s3://{S3_BUCKET_NAME}/{s3_key}"
    except Exception as e:
        logging.error(f"Failed to upload {file_name} to S3: {e}")
        return None

def process_message(message):
    """Processes a Kafka message containing a GRN (Goods Received Note)."""
    try:
        data = message.value  # Already a dictionary

        grn_id = data.get("grn_id")
        sender = data.get("sender")

        metadata = fetch_metadata()

        # ✅ Check if the GRN already exists
        processed_files = {(grn["grn_id"], grn["file_name"]) for grn in metadata["grns"]}

        new_entries = []  # Track newly added GRNs

        for attachment in data.get("attachments", []):
            file_name = attachment["file_name"]

            # ✅ Skip processing if this grn_id + file_name combination is already in metadata
            if (grn_id, file_name) in processed_files:
                logging.info(f"Skipping {file_name} from GRN {grn_id}: Already processed.")
                continue  # Skip this attachment

            file_data = base64.b64decode(attachment["file_data"])
            
            s3_path = upload_to_s3(file_name, file_data)
            if not s3_path:
                continue  # Skip if upload failed
            
            new_entry = {
                "grn_id": grn_id,
                "sender": sender,
                "received_at": datetime.utcnow().isoformat(),
                "file_name": file_name,
                "s3_path": s3_path,
                "status": "raw"
            }
            metadata["grns"].append(new_entry)
            new_entries.append(new_entry)

        if new_entries:
            upload_metadata(metadata)  # ✅ Only update metadata if new GRNs were added
            logging.info(f"Processed GRN {grn_id} with {len(new_entries)} new attachment(s).")
    
    except Exception as e:
        logging.error(f"Error processing message: {e}")

def consume_kafka():
    """Consumes messages from the GRN Kafka topic and processes them."""
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC_GRN,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            group_id="grn_processor_group",
            auto_offset_reset="latest",
            enable_auto_commit=False,
            value_deserializer=lambda v: json.loads(v.decode("utf-8"))
        )

        logging.info("Kafka Consumer for GRNs started, waiting for messages...")

        for message in consumer:
            process_message(message)
            consumer.commit()

    except Exception as e:
        logging.error(f"Kafka Consumer error: {e}")

if __name__ == "__main__":
    consume_kafka()
