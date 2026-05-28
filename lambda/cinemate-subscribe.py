import json, boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime, timezone

SUB_TABLE = "cinemate-subscriptions"
dynamodb  = boto3.resource("dynamodb")
table     = dynamodb.Table(SUB_TABLE)

headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type", "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS"}

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        return float(obj) if isinstance(obj, Decimal) else super().default(obj)

def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    method = event.get("httpMethod", "")
    params = event.get("queryStringParameters") or {}

    if method == "GET":
        email = params.get("email", "").strip().lower()
        if not email:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Missing email"})}
        resp  = table.query(KeyConditionExpression=Key("email").eq(email))
        items = resp.get("Items", [])
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"subscriptions": items}, cls=DecimalEncoder)}

    elif method == "POST":
        try: body = json.loads(event.get("body") or "{}")
        except: return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Invalid JSON"})}
        email      = body.get("email", "").strip().lower()
        title_year = body.get("title_year", "").strip()
        if not email or not title_year:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Missing email or title_year"})}
        table.put_item(Item={
            "email":      email,
            "title_year": title_year,
            "title":      body.get("title", ""),
            "director":   body.get("director", ""),
            "genre":      body.get("genre", ""),
            "rating":     Decimal(str(body["rating"])) if body.get("rating") else Decimal("0"),
            "year":       Decimal(str(body["year"]))   if body.get("year")   else Decimal("0"),
            "subscribed_at": datetime.now(timezone.utc).isoformat(),
        })
        return {"statusCode": 201, "headers": headers, "body": json.dumps({"message": f"Subscribed to {body.get('title', '')}"})}

    elif method == "DELETE":
        try: body = json.loads(event.get("body") or "{}")
        except: return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Invalid JSON"})}
        email      = body.get("email", "").strip().lower()
        title_year = body.get("title_year", "").strip()
        if not email or not title_year:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Missing fields"})}
        table.delete_item(Key={"email": email, "title_year": title_year})
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": "Removed subscription"})}

    return {"statusCode": 405, "headers": headers, "body": json.dumps({"error": "Method not allowed"})}