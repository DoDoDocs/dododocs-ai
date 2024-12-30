import aiohttp
import asyncio
import logging
from typing import Optional, List, Dict
from ktb_settings import *
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class APIClient:
    """API 요청 처리 클래스"""

    def __init__(self, model: str = MODEL, temperature: float = TEMPERATURE):
        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI(
            api_key=os.getenv('GOOGLE_API_KEY'),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

    async def generate_text_client(self, prompt: str, content: str, max_retries: int = MAX_RETRIES) -> Optional[str]:
        """텍스트 생성 API 호출"""
        attempt = 0
        while attempt < max_retries:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": content},
                    ],
                    temperature=self.temperature,
                    timeout=10000
                )
                if response.choices:
                    return response.choices[0].message.content
                else:
                    print(f"API 응답에 choices가 없습니다: {response}")
                    attempt += 1
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                print(f"API 호출 오류: {str(e)}")
                attempt += 1
                await asyncio.sleep(2 ** attempt)
        return None