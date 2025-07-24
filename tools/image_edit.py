import base64
import json
import os
from collections.abc import Generator
from io import BytesIO
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4
import httpx

import requests
from PIL import Image
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.file.file import File
from dotenv import find_dotenv
from flask.cli import load_dotenv
from pydantic import BaseModel, Field

from utils.image import upload_image
from utils.volcengine import Img2ImgRequest, Params, create_header
load_dotenv(find_dotenv())


class ImageToImageTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        prompt = tool_parameters.get("prompt", "")
        image: str = tool_parameters.get("image", "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream_i2i.jpeg")  # 获取图像参数, 应该是Dify File对象

        seed = tool_parameters.get("seed", None)
        url = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
        api_key = os.getenv("ARK_API_KEY")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": "doubao-seededit-3-0-i2i-250628",
            "prompt": prompt,
            "image": image,
            "response_format": "url",
            "size": "adaptive",
            "seed": 21,
            "guidance_scale": 5.5,
            "watermark": False,
        }
        try:
            with httpx.Client() as client:
                response = client.post(
                    url, headers=headers, json=payload, timeout=60
                )
                response.raise_for_status()
                result: dict = response.json()
                data: dict = result.get("data", [])[0]
                url = data.get("url", "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream_i2i.jpeg")

            # 上传图片
            response = httpx.get(url, timeout=60)

            content = response.content
            pil = Image.open(BytesIO(content))
            img_format = pil.format.lower() or "png"
            filename = f"{str(uuid4())}.{img_format}"

            image_url = upload_image(filename, data=content, prefix="seedream")

            yield self.create_text_message(image_url)
            yield self.create_json_message({"url": image_url})
            metadata = {"mime_type": f"image/{img_format}"}
            yield self.create_blob_message(content, meta=metadata)
            return
        except Exception as e:
            yield self.create_text_message(f"工具调用失败, 错误提示: {e}")
            return
