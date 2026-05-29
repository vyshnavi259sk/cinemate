# CineMate 🎬

A full-stack movie catalogue web application built on AWS cloud services.

> **Personal portfolio project** — built independently to demonstrate AWS cloud architecture skills.
> Dataset and all code are original. Conceptual architecture inspired by cloud computing coursework.

---

## Architecture

Will be updated soon

## DynamoDB Key Design

| Table | PK | SK | Notes |
|-------|----|----|-------|
| cinemate-movies | `director` | `title#year` | Composite SK prevents overwrites |
| cinemate-login | `email` | — | Simple lookup by email |
| cinemate-subscriptions | `email` | `title_year` | Per-user subscriptions |

### Indexes on cinemate-movies

| Index | Type | PK | SK | Purpose |
|-------|------|----|----|---------|
| director-rating-index | LSI | director | rating | Query a director's films by rating |
| genre-year-index | GSI | genre | year | Query any genre across all directors |

---

## Dataset

Claude generated the dataset as a JSON file directly from its training knowledge of well-known films, rather than from a downloadable third-party dataset file.

---

## Project Structure

```
cinemate/
├── movies.json                  — Source dataset (98 films)
├── README.md
├── .gitignore
├── database/
│   ├── setup_table.py           — Create DynamoDB tables + LSI + GSI
│   ├── load_movies.py           — Batch-load movies.json → DynamoDB
│   └── upload_posters.py        — Create S3 bucket + upload poster images
├── backend/
│   ├── app.py                   — Flask REST API (EC2 + ECS)
│   ├── requirements.txt
│   └── Dockerfile               — For ECS Fargate deployment
├── lambda/
│   ├── cinemate-movies.py           — GET /movies
│   ├── cinemate-search.py         — GET /search
│   ├── cinemate-genre.py          — GET /genre/{genre}
│   ├── cinemate-login.py                 — POST /login, POST /register
│   └── cinemate-subscribe.py             — GET/POST /subscribe, DELETE /subscription
└── frontend/
    ├── index.html               — Login page
    ├── register.html            — Registration page
    └── main.html                — Movie browser
```

---

## Features

- Login and registration with DynamoDB authentication
- Browse 98 films across 13 genres
- Search by title, director, genre, year, or minimum rating
- Per-user subscription system (add/remove)
- Backend selector — switch between EC2, ECS, Lambda live
- Genre filter strip
- Movie detail modal

---

## Deployment

### Prerequisites
- AWS Academy Learner Lab (LabRole / LabInstanceProfile)
- AWS CLI configured with session credentials
- Python 3.10+, Docker

### Step 1 — Database (run in CloudShell)
```bash
pip install boto3 requests --break-system-packages
python setup_table.py
python load_movies.py
python upload_posters.py
```

### Step 2 — EC2 Backend
```bash
# On EC2 instance (Amazon Linux 2023, t2.micro):
sudo yum install python3-pip -y
sudo pip3 install flask flask-cors boto3 gunicorn
# Copy app.py to instance, then:
sudo tee /etc/systemd/system/cinemate.service << EOF2
[Unit]
Description=CineMate Flask Backend
After=network.target
[Service]
User=root
WorkingDirectory=/home/ec2-user
ExecStart=/home/ec2-user/.local/bin/gunicorn --bind 0.0.0.0:80 --workers 2 app:app
Restart=always
[Install]
WantedBy=multi-user.target
EOF2
sudo systemctl enable cinemate
sudo systemctl start cinemate
```

### Step 3 — ECS Fargate
```bash
aws ecr create-repository --repository-name cinemate-backend
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
docker build -t cinemate-backend .
docker tag cinemate-backend:latest <account>.dkr.ecr.us-east-1.amazonaws.com/cinemate-backend:latest
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/cinemate-backend:latest
# Create ECS cluster + task definition + service via AWS Console
# Task role: LabRole, Execution role: LabRole, Port: 80, Public IP: enabled
```

### Step 4 — Lambda + API Gateway
1. Create 5 Lambda functions (Python 3.12, LabRole):
   - `cinemate-movies`, `cinemate-search`, `cinemate-genre`, `cinemate-login`, `cinemate-subscribe`
2. Set handler to `lambda_function.handler` for each
3. Create REST API in API Gateway with routes listed in Architecture section
4. Enable Lambda proxy integration on all routes
5. Enable CORS on all resources
6. Deploy to `prod` stage

### Step 5 — Frontend
1. Create S3 bucket with static website hosting enabled
2. Add public read bucket policy
3. Upload `frontend/` HTML files
4. Access via S3 website endpoint

---

## AWS Services Used

| Service | Purpose |
|---------|---------|
| DynamoDB | NoSQL database (movies, login, subscriptions) |
| S3 | Poster image storage + static frontend hosting |
| EC2 | Flask backend (Architecture 1) |
| ECS Fargate | Containerised backend (Architecture 2) |
| ECR | Docker image registry |
| Lambda | Serverless functions (Architecture 3) |
| API Gateway | HTTP routing to Lambda |

---

## Notes

- EC2 public IP is static (Elastic IP attached)
- ECS public IP changes on each task restart / lab session
- Lambda API Gateway URL is permanent
- AWS Academy LabRole credentials expire every few hours — refresh from AWS Details
- Backend Validation: Use F12 -> Network to monitor outgoing requests. Upon changing the backend selector, the IP address associated with site requests will update dynamically to match the chosen environment.

---

## License

MIT — free to use, fork, and build on.
