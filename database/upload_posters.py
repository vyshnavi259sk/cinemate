"""
CineMate - S3 Setup and Poster Uploader

1. Creates the S3 bucket for poster images.
2. Downloads poster thumbnails from a free public source (OMDb / placeholder).
3. Uploads them with the naming convention posters/<director_slug>/<title_slug>.jpg

Usage:
  python upload_posters.py

Note: This script uses placeholder poster images from picsum.photos
(freely licensed) so no API key is needed to get started.
Swap in real TMDB poster URLs by adding your TMDB API key below.
"""

import json
import boto3
import requests
import hashlib
from pathlib import Path
from botocore.exceptions import ClientError

BUCKET_NAME = "cinemate-posters-bucket"   # change to a globally unique name
REGION      = "us-east-1"
DATA_FILE   = Path(__file__).parent.parent / "movies.json"


# ---------------------------------------------------------------------------
# 1. Create bucket
# ---------------------------------------------------------------------------
def create_bucket():
    s3 = boto3.client("s3", region_name=REGION)
    try:
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={"LocationConstraint": REGION},
            )
        print(f"[OK] Bucket '{BUCKET_NAME}' created.")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"[SKIP] Bucket already exists.")
        else:
            raise


# ---------------------------------------------------------------------------
# 2. Upload posters
# ---------------------------------------------------------------------------
def slug(text: str) -> str:
    return text.lower().replace(" ", "_").replace(":", "").replace("'", "").replace(".", "")


def get_placeholder_url(movie_id: int, width: int = 300, height: int = 450) -> str:
    """
    Returns a deterministic placeholder image from picsum.photos.
    Each movie gets a consistent image based on its id.
    Replace this with a real TMDB poster URL if you have an API key:
      f"https://image.tmdb.org/t/p/w300{poster_path}"
    """
    seed = (movie_id % 1000) + 1
    return f"https://picsum.photos/seed/{seed}/{width}/{height}"


def upload_posters():
    s3 = boto3.client("s3", region_name=REGION)

    with open(DATA_FILE) as f:
        movies = json.load(f)

    print(f"Uploading {len(movies)} posters...")
    uploaded = 0

    for m in movies:
        director_s = slug(m["director"])
        title_s    = slug(m["title"])
        s3_key     = f"posters/{director_s}/{title_s}.jpg"

        # Download image
        url = get_placeholder_url(m["id"])
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [WARN] Could not fetch poster for '{m['title']}': {e}")
            continue

        # Upload to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=resp.content,
            ContentType="image/jpeg",
        )
        uploaded += 1

    print(f"[OK] Uploaded {uploaded} posters to s3://{BUCKET_NAME}/posters/")


if __name__ == "__main__":
    create_bucket()
    upload_posters()
