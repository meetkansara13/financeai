from datetime import datetime, timezone
import uuid


def build_meta():
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": str(uuid.uuid4())
    }


def success_response(message: str, data=None):
    return {
        "status": "success",
        "message": message,
        "data": data,
        "meta": build_meta()
    }


def error_response(message: str):
    return {
        "status": "error",
        "message": message,
        "data": None,
        "meta": build_meta()
    }