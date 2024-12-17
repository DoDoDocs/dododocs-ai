from typing import List, Optional
import os
import logging
from concurrent.futures import ThreadPoolExecutor
import tiktoken
from token_chunker import *
from ktb_settings import *


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
