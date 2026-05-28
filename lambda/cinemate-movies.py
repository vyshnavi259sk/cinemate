import json, boto3
from decimal import Decimal

TABLE_NAME = "cinemate-movies"
dynamodb   = boto3.resource("dynamodb")
table      = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        return float(obj) if isinstance(obj, Decimal) else super().default(obj)

def handler(event, context):
    headers = {"Access-Control-Allow-Origin": "*"}
    try:
        resp  = table.scan()
        items = resp.get("Items", [])
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"count": len(items), "movies": items}, cls=DecimalEncoder)
        }
    except Exception as e:
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}