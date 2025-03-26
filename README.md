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

## Potential Improvements
- Add comprehensive error handling
- Implement logging mechanisms
- Create unit and integration tests
- Add more robust validation checks

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License
[Specify the license under which this project is distributed]

## Contact
[Add contact information for the project maintainers]
