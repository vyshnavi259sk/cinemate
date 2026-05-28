import json, os, boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

TABLE_NAME = "cinemate-movies"
GSI_NAME   = "genre-year-index"
dynamodb   = boto3.resource("dynamodb")
table      = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        return float(obj) if isinstance(obj, Decimal) else super().default(obj)

def handler(event, context):
    params = event.get("pathParameters") or {}
    genre  = params.get("genre", "").strip()
    if not genre:
        return {"statusCode": 400, "headers": {"Access-Control-Allow-Origin": "*"}, "body": json.dumps({"error": "Missing genre"})}
    resp  = table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=Key("genre").eq(genre)
    )
    items = resp.get("Items", [])
    items.sort(key=lambda x: float(x.get("rating", 0)), reverse=True)
    return {"statusCode": 200, "headers": {"Access-Control-Allow-Origin": "*"}, "body": json.dumps({"genre": genre, "count": len(items), "movies": items}, cls=DecimalEncoder)}