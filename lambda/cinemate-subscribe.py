import json, boto3, os, hmac, hashlib, base64
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from datetime import datetime, timezone

SUB_TABLE = "cinemate-subscriptions"
dynamodb  = boto3.resource("dynamodb")
table     = dynamodb.Table(SUB_TABLE)

headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type,Authorization", "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS"}

# Must match CINEMATE_SECRET_KEY on the cinemate-login function — see README.
SECRET_KEY = os.environ.get("CINEMATE_SECRET_KEY", "dev-insecure-secret-change-me")

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        return float(obj) if isinstance(obj, Decimal) else super().default(obj)

def _get_header(event, name):
    for k, v in (event.get("headers") or {}).items():
        if k.lower() == name.lower():
            return v
    return None

def verify_token(token, email):
    if not token or "." not in token:
        return False
    payload, sig = token.rsplit(".", 1)
    expected_sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return False
    try:
        padded = payload + "=" * (-len(payload) % 4)
        decoded_email = base64.urlsafe_b64decode(padded.encode()).decode()
    except Exception:
        return False
    return decoded_email == email

def _authorized(event, email):
    auth = _get_header(event, "Authorization") or ""
    token = auth[7:] if auth.lower().startswith("bearer ") else auth
    return verify_token(token, email)

def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    method = event.get("httpMethod", "")
    params = event.get("queryStringParameters") or {}

    if method == "GET":
        email = params.get("email", "").strip().lower()
        if not email:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Missing email"})}
        if not _authorized(event, email):
            return {"statusCode": 401, "headers": headers, "body": json.dumps({"error": "Not authorized for this email"})}
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
        if not _authorized(event, email):
            return {"statusCode": 401, "headers": headers, "body": json.dumps({"error": "Not authorized for this email"})}
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
        if not _authorized(event, email):
            return {"statusCode": 401, "headers": headers, "body": json.dumps({"error": "Not authorized for this email"})}
        table.delete_item(Key={"email": email, "title_year": title_year})
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": "Removed subscription"})}

    return {"statusCode": 405, "headers": headers, "body": json.dumps({"error": "Method not allowed"})}
