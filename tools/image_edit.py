import base64
import json
import os
from collections.abc import Generator
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4
import httpx

import requests
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
            with (httpx.Client() as client):
                response = client.post(
                    url, headers=headers, json=payload, timeout=60
                )
                response.raise_for_status()
                result: dict = response.json()
                data: dict = result.get("data", [])[0]
                url = data.get("url", "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream_i2i.jpeg")

            # 上传图片
            filename = f"str(uuid4()).png"
            response = httpx.get(url)
            content = response.content
            image_url = upload_image(filename, data=content, prefix="seedream")

            yield self.create_text_message(image_url)
            yield self.create_json_message({"url": image_url})
            yield self.create_image_message(image_url)
            yield self.create_blob_message(content, meta={"mime_type": "image/png"})
            return
        except Exception as e:
            yield self.create_text_message(f"工具调用失败, 错误提示: {e}")
            return

        # TODO image to url
        # filename = str(uuid4())
        print(image)
        print(type(image))

        if not image:
            yield self.create_text_message("Error: Input image file is required.")
            return
        image_url = upload_image(image.filename, image.blob, prefix="seedream")
        body_pydantic = Img2ImgRequest(
            req_key="i2i_portrait_photo",
            prompt=prompt,
            image_input=image_url
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
        for image_base64 in images_base64:
            if not image_base64:
                continue
            # Decode the base64 image bytes
            # Create an ImageArtifact from the decoded bytes
            image_bytes = base64.b64decode(image_base64)
            id = str(uuid4())
            filename = f"{id}.png"

            url = upload_image(filename, image_bytes, prefix="seedream")
            urls.append(url)

        url = urls[0] if len(urls) > 0 else ""

        yield self.create_json_message({
            "url": url
        })
