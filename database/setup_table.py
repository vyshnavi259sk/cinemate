"""
CineMate - DynamoDB Table Setup
Creates the movies table with composite key, LSI, and GSI.

Key Design (same principles as any composite-key NoSQL design):
  PK  = director          (partition key)
  SK  = title#year        (sort key  — concatenation prevents overwrites
                           even if two films share a title in different years)

LSI  = director / rating  (query a director's films by rating)
GSI  = genre / year       (query any genre across all directors by year)

Usage:
  python setup_table.py
"""

import boto3
from botocore.exceptions import ClientError

TABLE_NAME = "cinemate-movies"
REGION     = "us-east-1"

def create_table():
    dynamodb = boto3.client("dynamodb", region_name=REGION)

    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=[
                {"AttributeName": "director",   "AttributeType": "S"},
                {"AttributeName": "title_year", "AttributeType": "S"},  # SK: "title#year"
                {"AttributeName": "rating",     "AttributeType": "N"},  # LSI sort key
                {"AttributeName": "genre",      "AttributeType": "S"},  # GSI partition key
                {"AttributeName": "year",       "AttributeType": "N"},  # GSI sort key
            ],
            KeySchema=[
                {"AttributeName": "director",   "KeyType": "HASH"},
                {"AttributeName": "title_year", "KeyType": "RANGE"},
            ],
            LocalSecondaryIndexes=[
                {
                    "IndexName": "director-rating-index",
                    "KeySchema": [
                        {"AttributeName": "director", "KeyType": "HASH"},
                        {"AttributeName": "rating",   "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "genre-year-index",
                    "KeySchema": [
                        {"AttributeName": "genre", "KeyType": "HASH"},
                        {"AttributeName": "year",  "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                    "ProvisionedThroughput": {
                        "ReadCapacityUnits":  5,
                        "WriteCapacityUnits": 5,
                    },
                }
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits":  5,
                "WriteCapacityUnits": 5,
            },
        )
        print(f"[OK] Table '{TABLE_NAME}' creation initiated.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"[SKIP] Table '{TABLE_NAME}' already exists.")
        else:
            raise

    # Wait until active
    waiter = dynamodb.get_waiter("table_exists")
    print("Waiting for table to become ACTIVE...")
    waiter.wait(TableName=TABLE_NAME)
    print("[OK] Table is ACTIVE and ready.")


if __name__ == "__main__":
    create_table()
