"""Object storage service using Emergent's storage API."""
import os
import uuid
import logging
import requests

logger = logging.getLogger("storage")

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = os.environ.get("APP_NAME", "cohortdata-hiring")

_storage_key = None


def init_storage():
    global _storage_key
    if _storage_key:
        return _storage_key
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY not set")
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": key}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    logger.info("Object storage initialized")
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


def upload_resume(candidate_email: str, filename: str, data: bytes, content_type: str) -> dict:
    ext = filename.split(".")[-1].lower() if "." in filename else "bin"
    if ext not in {"pdf", "doc", "docx"}:
        raise ValueError("Only PDF, DOC, DOCX resumes are allowed")
    safe_email = candidate_email.replace("@", "_at_").replace(".", "_")
    path = f"{APP_NAME}/resumes/{safe_email}/{uuid.uuid4()}.{ext}"
    result = put_object(path, data, content_type or "application/octet-stream")
    return {
        "storage_path": result["path"],
        "size": result.get("size", len(data)),
        "original_filename": filename,
        "content_type": content_type,
    }
