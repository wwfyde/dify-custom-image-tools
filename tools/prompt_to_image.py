import base64
import json
import os
from collections.abc import Generator
from io import BytesIO
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import requests
from PIL import Image
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dotenv import find_dotenv
from flask.cli import load_dotenv
from pydantic import BaseModel, Field

from utils.image import upload_image
from utils.volcengine import Params, create_header
load_dotenv(find_dotenv())

class RequestBody(BaseModel):
    """
    文档说明: https://www.volcengine.com/docs/85128/1526761#4e552e07
    接口日期: 2025-06-10
    """

    req_key: str = Field(
        ...,
        title="算法名称",
        description="算法名称，取固定值为high_aes_general_v30l_zt2i",
        examples=["high_aes_general_v30l_zt2i"],
    )
    prompt: str = Field(
        ...,
        title="提示词",
        description="用于生成图像的提示词 ，中英文均可输入",
    )
    use_pre_llm: bool | None = Field(
        True,
        title="是否开启文本扩写",
        description="开启文本扩写，会针对输入prompt进行扩写优化，如果输入prompt较短建议开启，如果输入prompt较长建议关闭, 默认值：false",
    )
    seed: int | None = Field(-1, title="随机种子")
    scale: float | None = Field(2.5, le=10, ge=1, title="影响文本描述的程度")
    width: int | None = Field(default=1328, ge=512, le=2048)
    height: int | None = Field(default=1328, ge=512, le=2048)
    return_url: bool | None = Field(
        None,
        title="是否返回图片链接",
        description="输出是否返回图片链接 （链接有效期为24小时）",
    )
    logo_info: dict | None = Field(None, title="水印信息")

class Create_imageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        prompt = tool_parameters.get("prompt", "")
        seed = tool_parameters.get("seed", None)

        body_pydantic = RequestBody(
            req_key="high_aes_general_v30l_zt2i",
            prompt=prompt,
        )
        if seed:
            body_pydantic.seed = seed
        body = body_pydantic.model_dump(exclude_unset=True, exclude_none=True)
        params = Params(
            access_key=os.getenv("SEEDREAM_ACCESS_KEY"),
            secret_key=os.getenv("SEEDREAM_SECRET_KEY"),
            body=body,
        )
        query_string = (
            urlencode(sorted(params.query_params.items()))
            if isinstance(params.query_params, dict)
            else params.query_params
        )
        url = params.base_url + "?" + query_string
        headers = create_header(params)
        response = requests.post(url=url, data=json.dumps(body), headers=headers)
        data = response.json()
        images_base64 = data.get("data", {}).get("binary_data_base64", [])
        urls = []
        images = []
        for image_base64 in images_base64:
            if not image_base64:
                continue
            # Decode the base64 image bytes
            # Create an ImageArtifact from the decoded bytes
            image_bytes = base64.b64decode(image_base64)
            id = str(uuid4())
            pil = Image.open(BytesIO(image_bytes))
            img_format = pil.format.lower()
            filename = f"{id}.{img_format}"

            images.append((image_bytes, img_format))
            url = upload_image(filename, image_bytes, prefix="seedream")
            urls.append(url)

        url = urls[0] if len(urls) > 0 else ""
        image_bytes, img_format = images[0] if len(images) >0 else None

        yield self.create_json_message({
            "url": url
        })

        yield self.create_text_message(url)
        metadata = {"mime_type": f"image/{img_format}"}
        yield self.create_blob_message(image_bytes, meta=metadata)
