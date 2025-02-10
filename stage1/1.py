from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64, email, os, io, pickle, logging, smtplib
from PyPDF2 import PdfReader
from email.mime.text import MIMEText
import hashlib

# Set up logging
logging.basicConfig(filename='stage1/invoice_processing.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
USER_ID = 'digitalinvoiceabcd@gmail.com'

# Gmail SMTP settings
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'digitalinvoiceabcd@gmail.com'  # Replace with your Gmail address
SMTP_PASSWORD = 'otun rvar nxrr wylq'      # Replace with your generated app password

def authenticate_gmail():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def fetch_emails():
    results = gmail_service.users().messages().list(userId=USER_ID, q='Invoice').execute()
    messages = results.get('messages', [])
    return messages

def process_email(message_id):
    message = gmail_service.users().messages().get(userId=USER_ID, id=message_id, format='raw').execute()
    msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))
    mime_msg = email.message_from_bytes(msg_str)
    sender_email = mime_msg['From']

    all_pdfs_valid = True  # Track overall PDF status for this email

    for part in mime_msg.walk():
        if part.get_content_type() == 'application/pdf':
            file_data = part.get_payload(decode=True)
            file_name = part.get_filename()

            if file_name:
                try:
                    pdf_reader = PdfReader(io.BytesIO(file_data))
                    if pdf_reader.pages:
                        os.makedirs('invoices', exist_ok=True)
                        with open(f'invoices/{file_name}', 'wb') as f:
                            f.write(file_data)
                        logging.info(f'Successfully saved: {file_name}')
                    else:
                        log_and_notify(f'Corrupted PDF detected: {file_name}')
                        all_pdfs_valid = False
                except Exception as e:
                    log_and_notify(f'Error reading PDF {file_name}: {e}')
                    all_pdfs_valid = False

    # Send confirmation if all PDFs were valid and sender is not the same as USER_ID
    if all_pdfs_valid and USER_ID not in sender_email:
        send_confirmation_email(sender_email)

def log_and_notify(message):
    logging.error(message)
    send_email_notification(message)

def send_email_notification(message):
    msg = MIMEText(message)
    msg['Subject'] = 'Invoice Processing Error'
    msg['From'] = SMTP_USERNAME
    msg['To'] = 'team@example.com'

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, 'team@example.com', msg.as_string())

def send_confirmation_email(recipient_email):
    msg = MIMEText('Your invoice has been successfully received and processed.')
    msg['Subject'] = 'Invoice Received Confirmation'
    msg['From'] = SMTP_USERNAME
    msg['To'] = recipient_email

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, recipient_email, msg.as_string())

if __name__ == '__main__':
    gmail_service = authenticate_gmail()
    messages = fetch_emails()
    for msg in messages:
        process_email(msg['id'])
