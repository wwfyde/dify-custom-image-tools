import base64
import json
import os
from collections.abc import Generator
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

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
        image: File = tool_parameters.get("image")  # 获取图像参数, 应该是Dify File对象
        if isinstance(image, list):
            image = image[0]

        image.url = f"http://agent.aimark.net.cn{image.url}" if image.url.startswith("/") else image.url
        seed = tool_parameters.get("seed", None)

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
