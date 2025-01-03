from typing import List, Optional
import os
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import tiktoken
import aiofiles
from token_chunker import *
from ktb_settings import *
import io
import re
import aiohttp
import uuid
from PIL import Image


from ktb_settings import get_openai_client
from ktb_prompts import DALLE_PROMPT

logger = logging.getLogger(__name__)


class FileUtils:
    """파일 처리 관련 유틸리티"""
    @staticmethod
    def find_files(directory: str, extensions: tuple) -> List[str]:
        """지정된 확장자를 가진 파일들을 찾음"""
        files = []
        for root, _, filenames in os.walk(directory):
            # if any(excl in root for excl in EXCLUDE_DIRS):
            #    continue
            files.extend(
                os.path.join(root, f)
                for f in filenames
                if f.endswith(extensions)
            )
        return files


class TextProcessor:
    """텍스트 처리 관련 유틸리티"""
    @staticmethod
    def count_tokens(text: str) -> int:
        try:
            encoding = tiktoken.encoding_for_model(GPT_MODEL)
            return len(encoding.encode(text, disallowed_special=()))
        except Exception as e:
            logger.error(f"토큰 계산 오류: {str(e)}")
            return len(text) // 4

    @staticmethod
    def split_text(text: str, max_tokens: int = GPT_MAX_TOKENS) -> List[str]:
        return chunker.chunk(text)


class ImageProcessor:
    """이미지 생성 및 README 업데이트 관련 유틸리티"""

    def __init__(self):
        self.client_gpt = get_openai_client()
        self.dalle_prompt = DALLE_PROMPT

    def read_description_from_readme(self, file_path="README.md"):
        """README 파일에서 'Overview' 섹션 추출"""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                # Description 섹션을 정규 표현식으로 추출
                description_match = re.search(
                    r"Overview\n(.*?)(### Main Purpose)", content, re.S)

                if description_match:
                    return description_match.group(1).strip()
                else:
                    raise ValueError(
                        "Could not find 'Overview' or 'Main Purpose' sections in the README.md")
        except FileNotFoundError:
            raise FileNotFoundError(f"File '{file_path}' does not exist.")

    async def download_image(self, url: str) -> bytes:
        """비동기적으로 이미지를 다운로드"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()

    def generate_image(self, description, new_size=(400, 400)):
        """DALL-E를 사용하여 이미지 생성"""
        response = self.client_gpt.images.generate(
            model="dall-e-3",
            prompt=self.dalle_prompt + description,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        image_data = asyncio.run(self.download_image(image_url))

        img = Image.open(io.BytesIO(image_data))
        resized_img = img.resize(new_size)

        image_path = f"generated_image_{uuid.uuid4()}.png"
        resized_img.save(image_path)

        return image_url, image_path

    def update_readme_with_image(self, file_path="README.md", image_path="./generated_image.png"):
        """README 파일에 이미지 삽입"""
        with open(file_path, "r+", encoding="utf-8") as file:
            content = file.read()

            # 'Preview' 섹션 뒤에 이미지를 삽입
            new_content = re.sub(
                r"(Preview\n)(.*?)(##|$)",
                f"Preview\n\n<img src='{
                    image_path}' width='400' height='400'/>\n\n\\3",
                content, flags=re.S
            )

            # 파일에 변경 사항 쓰기
            file.seek(0)
            file.write(new_content)
            file.truncate()
