from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from kafka import KafkaProducer
import base64, json, os, pickle, logging, email

log_file_path = os.path.join(os.path.dirname(__file__), 'invoice_processing.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
USER_ID = 'digitalinvoiceabcd@gmail.com'

# Initialize Kafka Producer
try:
    producer = KafkaProducer(
        bootstrap_servers='localhost:9092',
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
except Exception as e:
    logging.error(f"Kafka connection failed: {e}")
    exit(1)  # Exit if Kafka is unreachable

def authenticate_gmail():
    """Authenticate with Gmail API"""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('/Users/kriti.bharadwaj03/digitalInvoiceProcessing/credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def fetch_emails(gmail_service):
    """Fetch unread invoice emails from Gmail"""
    try:
        results = gmail_service.users().messages().list(userId=USER_ID, q='(subject:invoice OR subject:GRN) is:unread').execute()
        messages = results.get('messages', [])
        return messages
    except Exception as e:
        logging.error(f"Error fetching emails: {e}")
        return []

def send_to_kafka(gmail_service, message_id):
    """Extracts invoices from emails and sends them to Kafka"""
    try:
        message = gmail_service.users().messages().get(userId=USER_ID, id=message_id, format='raw').execute()
        msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
        mime_msg = email.message_from_bytes(msg_str)

        sender_email = mime_msg['From']
        subject = mime_msg.get('Subject', '').strip()  # Remove any leading/trailing spaces

        logging.info(f"Processing email {message_id} from {sender_email} with subject: '{subject}'")

        attachments = []

        # # Convert subject to uppercase for case-insensitive comparison
        # subject_upper = subject.upper()

        # Determine the Kafka topic based on subject
        if "invoice" in subject:
            kafka_topic = "email-invoices"
        elif "GRN" in subject:
            kafka_topic = "GRN"
        else:
            logging.info(f"Skipping email {message_id}, subject does not match: {subject}")
            return  # Skip emails that don't match

        
        for part in mime_msg.walk():
            if part.get_content_type() == 'application/pdf':
                file_data = part.get_payload(decode=True)
                file_name = part.get_filename()

                if file_name:
                    attachments.append({
                        "file_name": file_name,
                        "file_data": base64.b64encode(file_data).decode('utf-8')  # Encode for Kafka transmission
                    })

        # Ensure there is at least one attachment before sending
        if not attachments:
            logging.info(f"No attachments found in email {message_id}, skipping.")
            return

        email_data = {
            "email_id": message_id,
            "sender": sender_email,
            "attachments": attachments
        }
        if kafka_topic == "email-invoices":
            producer.send('email-invoices', email_data)
            producer.send('ocr', email_data)
            logging.info(f"Sent email {message_id} to 'email-invoices' and 'ocr'.")
        else:
            producer.send('grn', email_data)
            producer.send('ocr_grn', email_data)
            logging.info(f"Sent email {message_id} to 'grn' and 'ocr_grn'.")
        # logging.info(f"Sent email {message_id} with {len(attachments)} attachment(s) to Kafka.")

        # Mark email as read
        gmail_service.users().messages().modify(
            userId=USER_ID, id=message_id, body={'removeLabelIds': ['UNREAD']}
        ).execute()

    except Exception as e:
        logging.error(f"Error processing email {message_id}: {e}")

import time

if __name__ == '__main__':
    gmail_service = authenticate_gmail()

    while True:  
        messages = fetch_emails(gmail_service)

        if messages:
            for msg in messages:
                send_to_kafka(gmail_service, msg['id'])
        else:
            logging.info("No unread invoice emails found.")

        logging.info("Waiting for new emails...")
        time.sleep(30)  # Check emails every 30 seconds

