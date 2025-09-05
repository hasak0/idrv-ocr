# idrv-ocr

This project contains a Python script that leverages Amazon Web Services (AWS) for Optical Character Recognition (OCR) to automatically extract data from document images, specifically receipts and fuel meter readings. The script uses AWS Textract and Rekognition to parse text and structures the output into a clean, JSON-like format.

## PREREQUISITES:
Before running the script, ensure you have the following:
AWS Account: An active AWS account with the necessary permissions for S3, Textract, and Rekognition.
AWS Credentials: Your AWS credentials must be configured on your system (e.g., via the AWS CLI or environment variables).
Python 3: The script is written in Python 3.
Boto3 Library: The AWS SDK for Python. You can install it using pip:
pip install boto3

### USAGE:
The script is a command-line tool. You must provide the S3 bucket name and the document's file name as arguments.
python ocr.py <s3-bucket-name> <document-file-name>


**Example:**

To process a file named receipt.png located in an S3 bucket called my-documents-bucket, run the following command:

> python ocr.py my-documents-bucket receipt.png

The script will print the extracted data to the console.

## DATA TEMPLATES:

The script outputs data in one of two formats, depending on whether it identifies the document as a receipt or a meter reading.

**Receipt Data:**
~~~
{
    "document_type": "receipt",
    "provider": "Shell",
    "receipt_number": "123456789",
    "odometer": "123456",
    "date": "29/08/23",
    "total": "55.75",
    "items": [
        {"description": "Diesel", "price": "2.15", "litres": "25.93", "price_per_litre": "2.15"}
    ],
    "file_name": "receipt.png",
    "date_processed": "29/08/23",
    "payment_method": "Card",
    "card_number": "1234"
}
~~~
**Meter Reading Data:**
~~~

{
    "document_type": "meter",
    "provider": "Compac",
    "fuel": [
        {"Fuel Name": "Diesel", "Price": "55.75", "Litres": "25.93", "Price per Litres": "2.15"}
    ],
    "file_name": "meter_reading.jpg",
    "date_processed": "29/08/23"
}
~~~

