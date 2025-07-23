from collections.abc import Generator
from io import BytesIO
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dotenv import find_dotenv
from flask.cli import load_dotenv
from PIL import Image

load_dotenv(find_dotenv())


class UrlToFileTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        image = tool_parameters.get("image")
        if not image:
            yield self.create_text_message("图像不存在")
            return
        print(image)
        response = requests.get(image)
        image_bytes = response.content
        pil = Image.open(BytesIO(image_bytes))
        img_format = pil.format.lower()

        metadata = {"mime_type": f"image/{img_format}"}
        yield self.create_blob_message(image_bytes, meta=metadata)

