# DigitalInvoiceProcessing

## Overview
This project is an automated invoice processing pipeline that leverages Kafka for message streaming, OCR technology for document processing, and integrates with various cloud and database services.

## Project Structure

### Main Components

#### 1. Email Monitoring
- **File**: `Email_monitoring.py` (Kafka Producer)
- **Functionality**: Monitors emails and triggers the invoice processing workflow
- **Key Features**: 
  - Scans incoming emails for invoices and related documents
  - Initiates the processing pipeline by sending messages to Kafka topics

#### 2. Invoice Processing Workflow
##### 2.1 Invoice Uploader
- **File**: `invoice_uploader.py` (Kafka Subscriber)
- **Functionality**: Uploads invoices to Amazon S3
- **Key Features**:
  - Receives invoice documents from Kafka
  - Uploads documents to S3 storage
  - Prepares invoices for further processing

##### 2.2 OCR Pipeline
- **File**: `ocr_pipeline.py`
- **Functionality**: Performs Optical Character Recognition (OCR) on invoices
- **Key Features**:
  - Calls `main.py` in the Akaunting folder to initiate OCR process
  - Extracts text and data from invoice images/documents

#### 3. GRN (Goods Received Note) Processing
##### 3.1 GRN Uploader
- **File**: `grn_uploader.py` (Kafka Subscriber)
- **Functionality**: Uploads Goods Received Notes to Amazon S3
- **Key Features**:
  - Receives GRN documents
  - Uploads documents to S3 storage

##### 3.2 GRN OCR Pipeline
- **File**: `ocr_receipt_pipeline.py`
- **Functionality**: Performs OCR on Goods Received Notes
- **Key Features**:
  - Calls `ocr_receipt.py` in the Akaunting folder
  - Extracts text and data from GRN documents

### Supporting Components

#### 4. Database Access
- **File**: `db_access.py`
- **Functionality**: Provides database connection and interaction methods

#### 5. Validation and Processing
- **File**: `lakshya_validator.py`
  - Implements decrement logic for receipts

- **File**: `convert_po_to_bill.py`
  - Converts matched Purchase Orders to draft bills

- **File**: `bill_to_approval.py`
  - Sends bills for approval after 3-way validation

- **File**: `validator.py`
  - Performs validation logic between Purchase Orders and Invoices

#### 6. Token Management
- **File**: `token_manager.py`
- **Functionality**: Manages authentication tokens for accessing Zoho software

## Prerequisites
- Kafka messaging system
- Amazon S3 access
- Python 3.x
- Required Python libraries (specify in requirements.txt)
- Zoho software access credentials

## Setup and Installation
1. Clone the repository
2. Install required dependencies
   ```
   pip install -r requirements.txt
   ```
3. Configure environment variables for:
   - Kafka broker
   - S3 credentials
   - Zoho API tokens

## Running the Pipeline
To run the complete pipeline, open 5 separate terminals and execute:

Terminal 1: 
```
python Email_monitoring.py
```

Terminal 2:
```
python invoice_uploader.py
```

Terminal 3:
```
python ocr_pipeline.py
```

Terminal 4:
```
python grn_uploader.py
```

Terminal 5:
```
python ocr_receipt_pipeline.py
```

## Architecture
- Kafka-based event-driven architecture
- Microservices design
- OCR-powered document processing
- Cloud storage integration (S3)

# Invoice Pipeline Project

[... previous content remains the same ...]

## Credentials and Configuration

### Environment Variables and Configuration Files

#### 1. Database Configuration
##### `db_access.py` and `lakshya_validator.py`
- **Required Credential**: `DATABASE_URL`
- **Configuration**:
  ```python
  self.db_url = "postgresql://username:password@host:port/database"
  ```

#### 2. AWS S3 Configuration
##### `grn_uploader.py` and `invoice_uploader.py`
- **Required Credentials**:
  - `AWS_ACCESS_KEY`
  - `AWS_SECRET_KEY`
  - `S3_BUCKET_NAME`
- **Environment Setup**:
  ```bash
  export AWS_ACCESS_KEY='your_aws_access_key'
  export AWS_SECRET_KEY='your_aws_secret_key'
  export S3_BUCKET_NAME='your-s3-bucket-name'
  ```

#### 3. OCR API Configuration
##### `ocr_pdf_grn.py` and `Akaunting/OCR_receipt.py`
- **Required Credential**: `GEMINI_API_KEY`
- **Configuration**:
  ```python
  API_KEY = "your_gemini_api_key_here"
  ```

#### 4. Database Population
##### `populate_tables.py`
- **Note**: This is a sample file for populating tables during testing
- **Required Credential**: `DATABASE_URL`
  ```python
  DB_URL = "postgresql://username:password@host:port/database"
  ```

#### 5. Zoho Integration
##### `config.py`
**Configuration Template** (DO NOT include actual credentials in version control):
```python
# Zoho API Configuration
ZOHO_ORG_ID = ''  # Your Zoho Organization ID
ZOHO_CLIENT_ID = ''  # OAuth Client ID
ZOHO_CLIENT_SECRET = ''  # OAuth Client Secret
ZOHO_ACCESS_TOKEN = ''  # Initially obtained access token
ZOHO_REFRESH_TOKEN = ''  # Stored refresh token

# API Endpoints
ZOHO_API_DOMAIN = "https://www.zohoapis.in"
TOKEN_REFRESH_URL = "https://accounts.zoho.in/oauth/v2/token"

# Token Expiry
ACCESS_TOKEN_LIFESPAN = 3600  # 1 hour in seconds
```

#### 6. PostgreSQL Connection
##### `updater.py`
**Database Connection Configuration**:
```python
def get_db_connection():
    return psycopg2.connect(
        dbname="your_database_name",
        user="your_postgresql_username",
        password="your_postgresql_password",
        host="your_database_host",
        port="your_database_port"
    )
```

### Kafka Topics Configuration

#### Required Kafka Topics
1. `email-invoices`: For email invoice processing
2. `grn`: For Goods Received Notes
3. `ocr`: For OCR processing of invoices
4. `ocr_grn`: For OCR processing of Goods Received Notes

### Security and Best Practices
- **Never commit sensitive credentials to version control**
- Use environment variables or secure secret management systems
- Rotate credentials periodically
- Limit access to credentials
- Use `.env` files or secret management tools for local development


## Troubleshooting Credentials
- Verify all API keys and connection strings
- Check network connectivity
- Ensure proper IAM roles and permissions
- Validate token expiration and refresh mechanisms
