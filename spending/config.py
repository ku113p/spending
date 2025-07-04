import os


class Config:
    class Mongo:
        URI = os.environ.get("MONGO_URI", "mongodb://root:example@localhost:28017")
        DB_NAME = os.environ.get("MONGO_DB_NAME", "mydb")
        COLLECTION_NAME = os.environ.get("MONGO_COLLECTION_NAME", "mycollection")
