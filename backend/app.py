import os, json, boto3, hmac, hashlib, binascii, base64
from flask import Flask, request, jsonify
from flask_cors import CORS
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

app = Flask(__name__)
CORS(app, allow_headers=["Content-Type", "Authorization"])

REGION      = "us-east-1"
MOVIE_TABLE = "cinemate-movies"
LOGIN_TABLE = "cinemate-login"
SUB_TABLE   = "cinemate-subscriptions"
GSI_NAME    = "genre-year-index"

# Must match CINEMATE_SECRET_KEY on the Lambda architecture (lambda/cinemate-login.py,
# lambda/cinemate-subscribe.py) if you want a token from one backend to be accepted by
# another — see README "Auth" section. Falls back to an insecure dev value so the demo
# still runs if it's left unset; never rely on that fallback in a real deployment.
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


def authorized(email):
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.lower().startswith("bearer ") else auth
    return verify_token(token, email)

dynamodb = boto3.resource("dynamodb", region_name=REGION)
movies   = dynamodb.Table(MOVIE_TABLE)
logins   = dynamodb.Table(LOGIN_TABLE)
subs     = dynamodb.Table(SUB_TABLE)

class Dec(json.JSONEncoder):
    def default(self, o):
        return float(o) if isinstance(o, Decimal) else super().default(o)

app.json_encoder = Dec

def clean(item):
    return {k: float(v) if isinstance(v, Decimal) else v for k, v in item.items()}

def ok(data): return jsonify(data)
def err(msg, code=400): return jsonify({"error": msg}), code

@app.route("/health")
def health():
    return ok({"status": "ok", "backend": "EC2"})

@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(force=True)
    email = body.get("email", "").strip().lower()
    password = body.get("password", "").strip()
    if not email or not password:
        return err("Email and password required")
    resp = logins.get_item(Key={"email": email})
    user = resp.get("Item")
    if not user or not verify_password(password, user.get("password", "")):
        return err("Email or password is invalid", 401)
    return ok({
        "message": "Login successful",
        "email": email,
        "username": user.get("username", email),
        "token": make_token(email),
    })

@app.route("/register", methods=["POST"])
def register():
    body = request.get_json(force=True)
    email = body.get("email", "").strip().lower()
    username = body.get("username", "").strip()
    password = body.get("password", "").strip()
    if not email or not username or not password:
        return err("All fields required")
    existing = logins.get_item(Key={"email": email}).get("Item")
    if existing:
        return err("The email already exists", 409)
    logins.put_item(Item={"email": email, "username": username, "password": hash_password(password)})
    return ok({"message": "Registered successfully"}), 201

@app.route("/movies")
def list_movies():
    resp = movies.scan()
    items = [clean(i) for i in resp.get("Items", [])]
    return ok({"count": len(items), "movies": items})

@app.route("/movies/search")
def search_movies():
    title    = request.args.get("title", "").strip().lower()
    director = request.args.get("director", "").strip().lower()
    genre    = request.args.get("genre", "").strip()
    year     = request.args.get("year", "").strip()
    rating   = request.args.get("rating", "").strip()
    q        = request.args.get("q", "").strip().lower()

    if genre and year:
        resp = movies.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=Key("genre").eq(genre) & Key("year").eq(Decimal(year))
        )
        items = [clean(i) for i in resp.get("Items", [])]
    elif genre:
        resp = movies.query(
            IndexName=GSI_NAME,
            KeyConditionExpression=Key("genre").eq(genre)
        )
        items = [clean(i) for i in resp.get("Items", [])]
    else:
        resp = movies.scan()
        items = [clean(i) for i in resp.get("Items", [])]

    if q:        items = [i for i in items if q in i.get("title", "").lower()]
    if title:    items = [i for i in items if title in i.get("title", "").lower()]
    if director: items = [i for i in items if director in i.get("director", "").lower()]
    if year and not genre:
        items = [i for i in items if str(int(float(i.get("year", 0)))) == year]
    if rating:
        try: items = [i for i in items if float(i.get("rating", 0)) >= float(rating)]
        except: pass

    return ok({"count": len(items), "movies": items})

@app.route("/movies/genre/<path:genre_name>")
def movies_by_genre(genre_name):
    resp = movies.query(IndexName=GSI_NAME, KeyConditionExpression=Key("genre").eq(genre_name))
    items = [clean(i) for i in resp.get("Items", [])]
    return ok({"genre": genre_name, "count": len(items), "movies": items})

@app.route("/movies/director/<path:director_name>")
def movies_by_director(director_name):
    resp = movies.query(KeyConditionExpression=Key("director").eq(director_name))
    items = [clean(i) for i in resp.get("Items", [])]
    return ok({"director": director_name, "count": len(items), "movies": items})

@app.route("/subscriptions")
def get_subscriptions():
    email = request.args.get("email", "").strip().lower()
    if not email: return err("Missing email")
    if not authorized(email): return err("Not authorized for this email", 401)
    resp = subs.query(KeyConditionExpression=Key("email").eq(email))
    items = [clean(i) for i in resp.get("Items", [])]
    return ok({"email": email, "subscriptions": items})

@app.route("/subscribe", methods=["POST"])
def subscribe():
    body = request.get_json(force=True)
    email      = body.get("email", "").strip().lower()
    title_year = body.get("title_year", "").strip()
    title      = body.get("title", "").strip()
    director   = body.get("director", "").strip()
    genre      = body.get("genre", "").strip()
    rating     = body.get("rating")
    year       = body.get("year")
    if not email or not title_year:
        return err("Missing email or title_year")
    if not authorized(email): return err("Not authorized for this email", 401)
    subs.put_item(Item={
        "email":      email,
        "title_year": title_year,
        "title":      title,
        "director":   director,
        "genre":      genre,
        "rating":     Decimal(str(rating)) if rating else Decimal("0"),
        "year":       Decimal(str(year))   if year   else Decimal("0"),
    })
    return ok({"message": f"Subscribed to {title}"}), 201

@app.route("/subscription", methods=["DELETE"])
def unsubscribe():
    body = request.get_json(force=True)
    email      = body.get("email", "").strip().lower()
    title_year = body.get("title_year", "").strip()
    if not email or not title_year:
        return err("Missing fields")
    if not authorized(email): return err("Not authorized for this email", 401)
    subs.delete_item(Key={"email": email, "title_year": title_year})
    return ok({"message": "Removed subscription"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, debug=False)
