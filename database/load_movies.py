"""
CineMate - Load movies into DynamoDB
Reads movies.json and batch-writes all records.

Run AFTER setup_table.py.

Usage:
  python load_movies.py
"""

import json
import boto3
from decimal import Decimal
from pathlib import Path

TABLE_NAME = "cinemate-movies"
REGION     = "us-east-1"
DATA_FILE  = Path("/home/cloudshell-user/movies.json")


def load_movies():
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    table    = dynamodb.Table(TABLE_NAME)

    with open(DATA_FILE) as f:
        movies = json.load(f)

    print(f"Loading {len(movies)} movies into '{TABLE_NAME}'...")

    success = 0
    skipped = 0

    with table.batch_writer() as batch:
        for m in movies:
            # Compose the sort key: title#year
            title_year = f"{m['title']}#{m['year']}"

            # Build the poster S3 key (image will be uploaded separately)
            # Naming convention: posters/<director_slug>/<title_slug>.jpg
            director_slug = m["director"].lower().replace(" ", "_").replace(".", "")
            title_slug    = m["title"].lower().replace(" ", "_").replace(":", "").replace("'", "")
            poster_key    = f"posters/{director_slug}/{title_slug}.jpg"

            item = {
                "director":   m["director"],
                "title_year": title_year,
                "title":      m["title"],
                "year":       m["year"],
                "genre":      m["genre"],
                "rating":     Decimal(str(m["rating"])),
                "overview":   m["overview"],
                "cast":       m["cast"],
                "poster_key": poster_key,
            }

            batch.put_item(Item=item)
            success += 1

    print(f"[OK] Loaded {success} movies. Skipped: {skipped}.")


if __name__ == "__main__":
    load_movies()
