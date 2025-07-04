import os


class Config:
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://root:example@localhost:28017")
    MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "mydb")
    MONGO_COLLECTION_NAME = os.environ.get("MONGO_COLLECTION_NAME", "mycollection")
