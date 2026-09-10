import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException, status
from jose import JWTError, jwt

from core.config import MAX_BOT_TOKEN, MAX_INIT_DATA_MAX_AGE, SECRET_KEY

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def validate_max_init_data(init_data: str) -> dict:
    """Validate MAX Mini App initData and return the trusted user object.

    The signed string is the only source of identity. Never trust a user id
    supplied separately by the browser.
    """
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing initData hash")

    auth_date = int(pairs.get("auth_date", "0"))
    if not auth_date or time.time() - auth_date > MAX_INIT_DATA_MAX_AGE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired initData")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(
        b"WebAppData", MAX_BOT_TOKEN.get_secret_value().encode(), hashlib.sha256
    ).digest()
    calculated = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid initData signature")

    try:
        return json.loads(pairs["user"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid initData user") from exc


def create_access_token(user_id: int) -> str:
    return jwt.encode({"sub": str(user_id)}, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid access token") from exc
