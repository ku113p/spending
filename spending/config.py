import os


class Config:
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    TO_TEXT_URL = os.environ.get("TO_TEXT_URL", "http://127.0.0.1:9010/text")

    class Mongo:
        URI = os.environ.get("MONGO_URI", "mongodb://root:example@localhost:28017")
        DB_NAME = os.environ.get("MONGO_DB_NAME", "mydb")
        COLLECTION_NAME = os.environ.get("MONGO_COLLECTION_NAME", "mycollection")
    class TestData:
        IMAGE_FP = "/home/ku113p/Downloads/photo_2025-07-03_00-41-32.jpg"
        RECEIPT = """T-ELEVEN
Philippine Seven Corporation
Owned & Operated by: Philippine
Seven Corporation
VATREGTIN#000-390-189-1850
GF Hop Inn Tomas Morato, 312
Tomas Morato Ave.,Diliman,
Quezon City, Philippines
Tel #:NULL
06/14/2025（Sat）23:38:15
INV0ICE#2753133
RESET_CNT#O
STORE#3095
SN#:8300017
MIN#:18112010490311025
STAFF:CARLO CUBILLA
JandJC1beS1td28g
29.00V
PIATTOSCHEES40G
28.00V
GROWERSSALPISTA28G
63.00V
RiteNLiteCmbr250m1
30.00V
Total(4)
150.00
CASH
500.00
CHANGE
350.00
Vatable
133.93
VAT_Amt
16.07
Zero_Rated Sales
VAT Exempt Sales
0.00
0.00
Loyalty.No:
Name:
Address:
TIN:
Philippine Seven Corporation
7th Floor The Columbia Tower
Ortigas Avenue, Mandaluyong
City
TIN:000-390-189-000
BIR ACCr#
116-000390189-000346-19602
Date Issued: 08/01/2020
PTU #:
FP112018-116-0194632-00000
GET A CHANCE TO WIN A 1 MINUTE
SHOP ALL YOU CAN EXPERIENCE
WHEN YOU BUY A MINIMUM OF P200
WORTH OF PARTICIPATING
ITEMS.USE YOUR CLIQQ APP TO
JOIN. Per DTI FAIR TRADE
Permit Number:225068 Series of
2025.facebook.com/711philippines
- THIS IS AN INVOICE"""
