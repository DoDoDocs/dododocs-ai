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


logger = logging.getLogger(__name__)

class FileUtils:
    """파일 처리 관련 유틸리티"""
    @staticmethod
    def find_files(directory: str, extensions: tuple) -> List[str]:
        """지정된 확장자를 가진 파일들을 찾음"""
        files = []
        for root, _, filenames in os.walk(directory):
            #if any(excl in root for excl in EXCLUDE_DIRS):
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
            encoding = tiktoken.encoding_for_model("gpt-4o-mini")
            return len(encoding.encode(text, disallowed_special=()))
        except Exception as e:
            logger.error(f"토큰 계산 오류: {str(e)}")
            return len(text) // 4

    @staticmethod
    def split_text(text: str, max_tokens: int = GPT_MAX_TOKENS) -> List[str]:
        return chunker.chunk(text)

class AsyncFileIO:
    """비동기 파일 입출력 처리"""
    def __init__(self):
        self.io_pool = ThreadPoolExecutor(
            max_workers=multiprocessing.cpu_count() * 2
        )

    async def save_file(self, path: str, content: str):
        """비동기로 파일 저장"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.io_pool,
            lambda: open(path, "w", encoding="utf-8").write(content)
        )

    async def read_file(self, path: str) -> str:
        """비동기로 파일 읽기"""
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            return await f.read() 

