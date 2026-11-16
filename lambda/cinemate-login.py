import json, boto3, os, hmac, hashlib, binascii, base64

LOGIN_TABLE = "cinemate-login"
dynamodb    = boto3.resource("dynamodb")
table       = dynamodb.Table(LOGIN_TABLE)

headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type"}

# Shared secret for signing session tokens. MUST be set (and identical) on
# both the cinemate-login and cinemate-subscribe Lambda functions' env vars —
# see README "Auth" section. Falls back to an insecure dev value so the demo
# still runs if it's left unset, but that fallback must never be used in a
# real deployment.
SECRET_KEY = os.environ.get("CINEMATE_SECRET_KEY", "dev-insecure-secret-change-me")

PBKDF2_ITERATIONS = 100_000

def hash_password(password):
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"{binascii.hexlify(salt).decode()}${binascii.hexlify(dk).decode()}"

def verify_password(password, stored):
    try:
        salt_hex, hash_hex = stored.split("$")
        salt = binascii.unhexlify(salt_hex)
        expected = binascii.unhexlify(hash_hex)
    except (ValueError, binascii.Error):
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return hmac.compare_digest(dk, expected)

def make_token(email):
    payload = base64.urlsafe_b64encode(email.encode()).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"

def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": headers, "body": ""}

    path = event.get("path", "")

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
        table.put_item(Item={"email": email, "username": username, "password": hash_password(password)})
        return {"statusCode": 201, "headers": headers, "body": json.dumps({"message": "Registered successfully"})}

    else:
        if not email or not password:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Email and password required"})}
        resp = table.get_item(Key={"email": email})
        user = resp.get("Item")
        if not user or not verify_password(password, user.get("password", "")):
            return {"statusCode": 401, "headers": headers, "body": json.dumps({"error": "Email or password is invalid"})}
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "message": "Login successful",
                "email": email,
                "username": user.get("username", email),
                "token": make_token(email),
            }),
        }
