import hashlib
import hmac
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field


class Params(BaseModel):
    access_key: str
    secret_key: str
    body: dict
    method: Literal["GET", "POST", "PUT", "DELETE"] = "POST"
    base_url: str = "https://visual.volcengineapi.com"
    query_params: dict | str = "Action=CVProcess&Version=2022-08-31"
    region: str = "cn-north-1"
    service: str = "cv"
    algorithm: str = "HMAC-SHA256"


class SeedreamVisionServiceIdentity(Enum):
    Portrait = "i2i_portrait_photo"
    General = "high_aes_general_v30l_zt2i"


class Img2ImgRequest(BaseModel):
    """
    文档说明: https://www.volcengine.com/docs/85128/1602212
    火山引擎::智能视觉服务::智能绘图::图生图
    """

    req_key: str = SeedreamVisionServiceIdentity.Portrait.value
    image_input: str = Field(..., description="图片URL")
    prompt: str | None = Field(None, description="生图提示")
    width: int | None = Field(default=1328, ge=512, le=2048)
    height: int | None = Field(default=1328, ge=512, le=2048)
    gpen: float | None = Field(
        default=0.4,
        ge=0,
        le=1,
        description="高清处理效果，越高人脸清晰度越高，建议使用默认值",
        examples=[0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1],
    )
    skin: float | None = Field(default=0.3)
    seed: int | None = Field(-1, title="随机种子")


def sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def get_signature_key(key: str, date: str, region: str, service: str) -> bytes:
    key_bytes = key.encode("utf-8")
    key_date = sign(key_bytes, date)
    key_region = sign(key_date, region)
    key_service = sign(key_region, service)
    key = sign(key_service, "request")
    return key


def get_authorization_string():
    pass


def create_header(
    params: Params,
) -> dict:
    """创建Header"""
    signed_headers = "content-type;host;x-content-sha256;x-date"
    content_type = "application/json"
    payload_hash = hashlib.sha256(json.dumps(params.body).encode("utf-8")).hexdigest()
    # current_datetime = datetime.now(timezone.utc).isoformat(timespec="seconds")
    now = datetime.now(timezone.utc)
    current_datetime = now.strftime("%Y%m%dT%H%M%SZ")
    # current_date = now.date().isoformat()
    current_date = now.strftime("%Y%m%d")
    host = httpx.URL(params.base_url).host
    canonical_headers = (
        f"content-type:{content_type}\nhost:{host}\nx-content-sha256:{payload_hash}\nx-date:{current_datetime}\n"
    )
    credential_scope = f"{current_date}/{params.region}/{params.service}/request"
    canonical_uri = "/"
    # query_string = httpx.URL(params.base_url, params=params.query_params).query.decode()

    query_string = (
        urlencode(sorted(params.query_params.items())) if isinstance(params.query_params, dict) else params.query_params
    )

    canonical_request = (
        f"{params.method}\n{canonical_uri}\n{query_string}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )
    string_to_sign = f"{params.algorithm}\n{current_datetime}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    signing_key = get_signature_key(params.secret_key, current_date, params.region, params.service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization_header = f"{params.algorithm} Credential={params.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

    headers = {
        "X-Date": current_datetime,
        "Authorization": authorization_header,
        "X-Content-Sha256": payload_hash,
        "Content-Type": content_type,
    }
    return headers
