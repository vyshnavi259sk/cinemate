import json, boto3

LOGIN_TABLE = "cinemate-login"
dynamodb    = boto3.resource("dynamodb")
table       = dynamodb.Table(LOGIN_TABLE)

headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type"}

def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    method = event.get("httpMethod", "")
    path   = event.get("path", "")

    try:
        body = json.loads(event.get("body") or "{}")
    except:
        return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Invalid JSON"})}

    email    = body.get("email", "").strip().lower()
    password = body.get("password", "").strip()
    username = body.get("username", "").strip()

    if "/register" in path:
        if not email or not username or not password:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "All fields required"})}
        existing = table.get_item(Key={"email": email}).get("Item")
        if existing:
            return {"statusCode": 409, "headers": headers, "body": json.dumps({"error": "The email already exists"})}
        table.put_item(Item={"email": email, "username": username, "password": password})
        return {"statusCode": 201, "headers": headers, "body": json.dumps({"message": "Registered successfully"})}

    else:
        if not email or not password:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Email and password required"})}
        resp = table.get_item(Key={"email": email})
        user = resp.get("Item")
        if not user or user.get("password") != password:
            return {"statusCode": 401, "headers": headers, "body": json.dumps({"error": "Email or password is invalid"})}
        return {"statusCode": 200, "headers": headers, "body": json.dumps({"message": "Login successful", "email": email, "username": user.get("username", email)})}