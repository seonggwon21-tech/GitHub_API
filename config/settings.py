import os

from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "seonggwon21-tech")
# Dedicated sandbox repo for write-path (create/update/delete) tests. Created
# automatically by the write_repo fixture if it does not yet exist, so the
# portfolio repos stay free of test-generated issues and labels.
GITHUB_WRITE_REPO = os.getenv("GITHUB_WRITE_REPO", "qa-sandbox")

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"
