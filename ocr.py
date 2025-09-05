import boto3
import re
from re import sub
import datetime
import io
import sys

receipt_template = {
    "document_type":"receipt",
    "provider":"",
    "receipt_number":"",
    "odometer":"",
    "date": "",
    "total": "",
    "items": [],
    "file_name": "",
    "date_processed":"",
    "payment_method":"",
    "card_number":""
}

meter_template = {
    "document_type":"meter",
    "provider":"",
    "fuel":[],
    "file_name":"",
    "date_processed":""
}


bucket = str(sys.argv[1])
document = str(sys.argv[2])

datenow = datetime.datetime.now()
creationDate = datenow.strftime("%d/%m/%y")
receipt_template["date_processed"] = creationDate
meter_template["date_processed"] = creationDate

s3_object = boto3.resource('s3').Object(bucket, document)
try:
    s3_response = s3_object.get()
except:
    print("Invalid bucket or file name.")
stream = io.BytesIO(s3_response['Body'].read())
bucket_location = boto3.client('s3').get_bucket_location(Bucket=bucket)

text = boto3.client("textract")
image_binary = stream.getvalue()
try:
    response = text.detect_document_text(Document={'S3Object': {'Bucket':bucket, 'Name':document}})
except:
    print("There was an error fetching the S3 Object.")

receipt_template["file_name"] = document
meter_template["file_name"] = document
doctype = 1
for i, block in enumerate(response["Blocks"]):
    if block["BlockType"] == "LINE":
        receipt = re.search(r"(receipt no).?", block["Text"], re.IGNORECASE)
        abn = re.search(r"abn|ABN", block["Text"], re.IGNORECASE)
        total = re.search(r"Total|TOTAL", block["Text"])
        if abn or receipt or total is not None:
            doctype = 0
            break
########## RECEIPT #################################################################################################################
if doctype == 0:
    for i, block in enumerate(response["Blocks"]):
        if block["BlockType"] == "LINE":
            timetemp = re.search(r"[0-9][0-9]:[0-9][0-9]", block["Text"])
            date = re.search(r"(?:(?:31(\/|-|\.)(?:0?[13578]|1[02]|(?i:Jan|Mar|May|Jul|Aug|Oct|Dec)))\1|(?:(?:29|30)(\/|-|\.)(?:0?[1,3-9]|1[0-2]|(?i:Jan|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))\2))(?:(?:1[6-9]|[2-9]\d)?\d{2})|(?:29(\/|-|\.)(?:0?2|(?:Feb))\3(?:(?:(?:1[6-9]|[2-9]\d)?(?:0[48]|[2468][048]|[13579][26])|(?:(?:16|[2468][048]|[3579][26])00))))|(?:0?[1-9]|1\d|2[0-8])(\/|-|\.)(?:(?:0?[1-9]|(?i:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep))|(?:1[0-2]|(?:Oct|Nov|Dec)))\4(?:(?:1[6-9]|[2-9]\d)?\d{2})", block["Text"], re.MULTILINE)
            total = re.search(r"Total|TOTAL", block["Text"])
            odometer = re.search(r"Odometer|ODOMETER", block["Text"])
            receipt = re.search(r"(receipt no).?", block["Text"], re.IGNORECASE)
            num = re.search(r"(\b\d+(?:[\.,]\d+)?\b(?!(?:[\.,]\d+)|(?:\s*(?:%|percent))))", block["Text"])
            price = re.search(r"[$€]{1}(?P<amount>[\d,\.]+(\.\d{2}){0,})\b", block["Text"], re.MULTILINE)
            items = re.search(r"AdBlue|Ad blue|Diese(l*)|ADB|Adb", block["Text"], re.MULTILINE | re.IGNORECASE)
            digits = response["Blocks"][i+1]["Text"]
            cardno = re.search(r"Card No|Fuel Card", block["Text"], re.IGNORECASE)

            # PROVIDER
            cash = re.search(r"EFTPOS|EFIPOS", block["Text"], re.IGNORECASE)
            if cash is not None:
                receipt_template["provider"] = "Cash"
            if receipt_template["provider"] != "Cash":
                if "coles" in block["Text"].lower():
                    receipt_template["provider"] = "Shell"
                if "shell" in block["Text"].lower():
                    receipt_template["provider"] = "Shell" 
                if "pacific" in block["Text"].lower():
                    receipt_template["provider"] = "Pacific Petroleum"
                if "westside" in block["Text"].lower():
                    receipt_template["provider"] = "Westside Petroleum"
                if "BP" in block["Text"]:
                    receipt_template["provider"] = "BP"
            
            # PAYMENT METHOD
            if receipt_template["payment_method"] == "":
                card = re.search(r"(FUEL|PACIFIC|SHELL) *(Card)", block["Text"], re.IGNORECASE) 
                cash = re.search(r"EFTPOS|EFIPOS", block["Text"], re.IGNORECASE)
                if card is not None:
                    receipt_template["payment_method"] = "Card"
                if cash is not None:
                    receipt_template["payment_method"] = "Cash"
            
            # CARD NUMBER
            if cardno is not None:
                number = re.search(r"^(\b\d+(?:[\.,]\d+)?\b(?!(?:[\.,]\d+)|(?:\s*(?:%|percent))))", block["Text"])
                if number is not None:
                    receipt_template["odometer"] = num.group()
                else:
                    for x in range(2):
                        if response["Blocks"][i+x]["BlockType"] == "LINE":
                            skip = response["Blocks"][i+x]["Text"]
                            number = re.search(r"^(\b\d+(?:[\.,]\d+)?\b(?!(?:[\.,]\d+)|(?:\s*(?:%|percent))))", skip)
                            if number is not None:
                                receipt_template["card_number"] = number.group()
                                break

            # DATE
            if date is not None:
                receipt_template["date"] = date.group()
                if timetemp is not None:
                    receipt_template["date"] = date.group() +" "+ timetemp.group()

            # TOTAL
            if total is not None:
                if price is not None:
                    receipt_template["total"] = price.group()
                else:
                    total = ''.join(c for c in response["Blocks"][i+1]["Text"] if c in digits +"."+",")
                    if total == '':
                        total = ''.join(c for c in response["Blocks"][i-1]["Text"] if c in digits +"."+",")
                    receipt_template["total"] = total

            # ODOMETER
            if odometer is not None:
                if num is not None:
                    receipt_template["odometer"] = num.group()
                else:
                    for x in range(2):
                        if response["Blocks"][i+x]["BlockType"] == "LINE":
                            skip = response["Blocks"][i+x]["Text"]
                            digits = re.search(r"(\b\d+(?:[\.,]\d+)?\b(?!(?:[\.,]\d+)|(?:\s*(?:%|percent))))", skip)
                            if digits is not None:
                                receipt_template["odometer"] = digits.group()
                                break


            # RECEIPT NO
            if receipt is not None:
                if num is not None:
                    receipt_template["receipt_number"] = num.group()
                else:
                    receipt_template["receipt_number"] = "Not Given"
            
            # ITEMS
            itemPrice = None
            liter = None
            amount = None
            if items is not None:
                item = ""
                for z in range(5):
                    if response["Blocks"][i+z]["BlockType"] == "LINE":
                        skip = response["Blocks"][i+z]["Text"]
                        withCurrency = re.search(r"[$](\d*\.?\d+)$", skip, re.MULTILINE)
                        if withCurrency is not None:
                            itemPrice = withCurrency.group()
                            break
                if itemPrice is None:     
                    for z in range(5):
                        if response["Blocks"][i+z]["BlockType"] == "LINE":
                            skip = response["Blocks"][i+z]["Text"]
                            noCurrency = re.search(r"^[0-9]+(\.[0-9]+)?", skip, re.MULTILINE)
                            if noCurrency is not None:
                                itemPrice = "${}".format(noCurrency.group())
                                break
                if itemPrice is None:
                    for z in range(5):
                        if response["Blocks"][i+z]["BlockType"] == "LINE":
                            skip = response["Blocks"][i+z]["Text"]
                            asterisk = re.search(r"(\d*\.?\d+)[*]", skip, re.MULTILINE)
                            if asterisk is not None:
                                itemPrice = asterisk.group()
                                break

                if liter is None:
                    for x in range(10):
                        if response["Blocks"][i+x]["BlockType"] == "LINE":
                            skip = response["Blocks"][i+x]["Text"]
                            ppliter = re.search(r"(\d*\.?\d+) ?(([$]*\/ *L))", skip, re.MULTILINE | re.IGNORECASE)
                            if ppliter is not None:
                                p = ppliter.group()
                                dec = re.search(r"\d*\.?\d+", p)
                                liter = float(dec.group())
                                break
                if liter is None:
                    for x in range(10):
                        if response["Blocks"][i+x]["BlockType"] == "LINE":
                            skip = response["Blocks"][i+x]["Text"]
                            ltliter = re.search(r"[$](\d*\.?\d+) ?(([$]*\/ *L)|Lt)", skip, re.MULTILINE | re.IGNORECASE)
                            if ltliter is not None:
                                p = ltliter.group()
                                dec = re.search(r"\d*\.?\d+", p)
                                liter = float(dec.group())
                                break
                if liter is None:
                    for x in range(10):
                        if response["Blocks"][i+x]["BlockType"] == "LINE":
                            skip = response["Blocks"][i+x]["Text"]
                            c_liter = re.search(r"(\d*\.?\d+) ?([c|O]\/L)", skip, re.MULTILINE | re.IGNORECASE)
                            if c_liter is not None:
                                c = c_liter.group()
                                dec = re.search(r"\d*\.?\d+", c)
                                liter = float(dec.group()) / 100
                                break
                if liter is None:
                    for x in range(10):
                        if response["Blocks"][i+x]["BlockType"] == "LINE":
                            skip = response["Blocks"][i+x]["Text"]
                            prliter = re.search(r"([$]\/L)(\d*\.?\d+)", skip)
                            if prliter is not None:
                                p = prliter.group()
                                dec = re.search(r"\d*\.?\d+", p)
                                liter = float(dec.group())
                                break
                if liter is None:
                    for x in range (7):
                        if response["Blocks"][i+x]["BlockType"] == "LINE":
                            skip = response["Blocks"][i+x]["Text"]
                            withCurrency = re.search(r"^[$](\d*\.?\d+)$", skip, re.MULTILINE)
                            if withCurrency is not None:
                                c = withCurrency.group()
                                dec = re.search(r"\d*\.?\d+", c)
                                liter = float(dec.group())
                                amount = float(response["Blocks"][i+1]["Text"])
                                break
                if amount is None:
                    for x in range (10):
                        if response["Blocks"][i+x]["BlockType"] == "LINE":
                                skip = response["Blocks"][i+x]["Text"]
                                count = re.search(r"(\d*\.?\d+) *(L)", skip)
                                if count is not None:
                                    c = count.group()
                                    dec = re.search(r"\d*\.?\d+", c)
                                    amount = float(dec.group())
                                    break
                if amount is None:
                    for x in range (7):
                        if response["Blocks"][i+x]["BlockType"] == "LINE":
                                skip = response["Blocks"][i+x]["Text"]
                                qty = re.search(r"QTY", skip)
                                print(skip, type(skip), "next")
                                if qty is not None:
                                    count = re.search(r"(\d*\.?\d+)", skip)
                                    if count is not None:
                                        amount = count.group()
                                    else:
                                        for z in range(5):
                                            if response["Blocks"][i+x+z]["BlockType"] == "LINE":
                                                next = response["Blocks"][i+x+z]["Text"]
                                                print("+++++++++++++++++++++++++")
                                                print(next)
                                                count = re.search(r"(\d*\.?\d+)", next)
                                                if count is not None:
                                                    c = count.group()
                                                    dec = re.search(r"\d*\.?\d+", c)
                                                    amount = float(dec.group())
                                                    break

                if items.group().lower == "adb":
                    item = "Adblue"
                else:
                    item = items.group()
                diese = re.search(r"diese", item, re.IGNORECASE)
                if diese is not None:
                    item = "Diesel"
                receipt_template["items"].append({"description": item, "price": itemPrice, "litres": amount, "price_per_litre": liter})



    receipt_template["total"] = float(sub(r'[^\d.]', '', receipt_template["total"]))

    if receipt_template["items"] == []:
        receipt_template["items"].append("No item(s) detected.")
    for item in receipt_template["items"]:
        if item != "No item(s) detected.":
            item["price"] = float(sub(r'[^\d.]', '', item["price"]))
    if receipt_template["receipt_number"] == "":
        receipt_template["receipt_number"] = "Not Given"
    if receipt_template["odometer"] == "":
        receipt_template["odometer"] = "Not Given"   
    if receipt_template["date"] == "":
        receipt_template["date"] = "Not Given"

############# METER ##################################################################################################
else:
    rekognition = boto3.client('rekognition')
    hubometer = rekognition.detect_text(Image={'S3Object':{'Bucket':bucket,'Name':document}})
    for i, block in enumerate(hubometer["TextDetections"]):
        if block["Type"] == "LINE":
            item = re.search(r"Adblue|Diesel", block["DetectedText"], re.IGNORECASE)
            dec = re.search(r"(\d*\.?\d+)$", block["DetectedText"])

            # PROVIDER
            if "compac" in block["DetectedText"].lower():
                meter_template["provider"] = "Compac"
            if "pacific" in block["DetectedText"].lower():
                meter_template["provider"] = "Pacific Petroleum"
            
            if dec is not None:
                fuelprice = dec.group()
                for x in range(10):
                    if hubometer["TextDetections"][i+x]["Type"] == "LINE":
                        for x in range (10):
                            if hubometer["TextDetections"][i+x]["Type"] == "LINE":
                                skip = hubometer["TextDetections"][i+x]["DetectedText"]
                                litre = re.search(r"(\d*\.\d+)$", skip)
                                if litre is not None:
                                    fuellitre = litre.group()
                                    for z in range (10):
                                        if hubometer["TextDetections"][i+z]["Type"] == "LINE":
                                            skip = hubometer["TextDetections"][i+z]["DetectedText"]
                                            perlitre = re.search(r"(\d*\.\d+)$", skip)
                                            if perlitre is not None:
                                                costperlitre = perlitre.group()
                                                break
                                    break
                meter_template["fuel"].append({"Fuel Name":"", "Price":fuelprice, "Litres":fuellitre, "Price per Litres":costperlitre})

if doctype == 0:
    print(receipt_template)
else:
    print(meter_template)

















