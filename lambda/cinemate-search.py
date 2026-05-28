import json, boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

TABLE_NAME = "cinemate-movies"
GSI_NAME   = "genre-year-index"
dynamodb   = boto3.resource("dynamodb")
table      = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        return float(obj) if isinstance(obj, Decimal) else super().default(obj)

def handler(event, context):
    params   = event.get("queryStringParameters") or {}
    q        = params.get("q", "").strip().lower()
    title    = params.get("title", "").strip().lower()
    director = params.get("director", "").strip().lower()
    genre    = params.get("genre", "").strip()
    year     = params.get("year", "").strip()
    rating   = params.get("rating", "").strip()
    headers  = {"Access-Control-Allow-Origin": "*"}

    try:
        if genre and year:
            resp  = table.query(
                IndexName=GSI_NAME,
                KeyConditionExpression=Key("genre").eq(genre) & Key("year").eq(Decimal(year))
            )
            items = resp.get("Items", [])
        elif genre:
            resp  = table.query(
                IndexName=GSI_NAME,
                KeyConditionExpression=Key("genre").eq(genre)
            )
            items = resp.get("Items", [])
        else:
            resp  = table.scan()
            items = resp.get("Items", [])

        if q:        items = [i for i in items if q in i.get("title","").lower()]
        if title:    items = [i for i in items if title in i.get("title","").lower()]
        if director: items = [i for i in items if director in i.get("director","").lower()]
        if year and not genre:
            items = [i for i in items if str(int(float(i.get("year",0)))) == year]
        if rating:
            try: items = [i for i in items if float(i.get("rating",0)) >= float(rating)]
            except: pass

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"count": len(items), "movies": items}, cls=DecimalEncoder)
        }
    except Exception as e:
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}