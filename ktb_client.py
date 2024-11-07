import requests
import logging
from typing import Iterator, Optional, List, Dict, Any
import pprint
import asyncio

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatClient:
    """FastAPI 서버와 통신하는 채팅 클라이언트"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        ChatClient 초기화
        
        Args:
            base_url (str): API 서버 기본 URL
        """
        self.base_url = base_url.rstrip('/')
        
    def chat(self, repo_name: str, query: str, chat_history: Optional[List[Dict[str, Any]]] = None) -> Iterator[str]:
        """
        채팅 API에 요청을 보내고 스트리밍 응답을 처리
        
        Args:
            repo_name (str): 저장소 URL
            query (str): 사용자 질의
            chat_history (Optional[List[Dict[str, Any]]]): 이전 대화 내용

        Yields:
            str: 스트리밍 응답의 각 청크

        Raises:
            requests.RequestException: API 요청 실패 시
        """
        try:
            # API 엔드포인트 URL
            url = f"{self.base_url}/chat"

            # 요청 바디 구성
            payload = {
                "git_path": repo_name,
                "query": query,
                "chat_history": chat_history or []
            }

            # 스트리밍 응답 요청
            with requests.post(url, json=payload, stream=True) as response:
                response.raise_for_status()

                # 스트리밍 응답 처리
                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        yield chunk

        except requests.RequestException as e:
            logger.error(f"API 요청 실패: {str(e)}")
            raise

    def db(self, git_path: str, s3_path: str) -> Dict[str, Any]:
        """
        문서 생성 API에 요청을 보내고 응답을 반환
        
        Args:
            git_path (str): 저장소 경로

        Returns:
            Dict[str, Any]: API 응답 데이터

        Raises:
            requests.RequestException: API 요청 실패 시
        """
        try:
            # API 엔드포인트 URL
            url = f"{self.base_url}/generate_doc"

            # 요청 바디 구성
            payload = {"git_path": git_path.lstrip('./'),
                       "s3_path": s3_path}

            # 요청 보내기
            response = requests.post(url, json=payload)
            response.raise_for_status()  # 상태 코드 확인

            # JSON 응답 반환
            return response.json()

        except requests.RequestException as e:
            logger.error(f"API 요청 실패: {str(e)}")
            raise


async def main():
    client = ChatClient()
    query = "How MemberController works?"
    #repo_url = "https://github.com/kakaotech-25/moheng.git"
    repo_url = "https://github.com/spring-projects/spring-boot.git"
    s3_path = "spring-boot-main.zip"

    try:
        response = client.db(git_path=repo_url, s3_path=s3_path)
        pprint.pprint(response)

        '''
        # 첫 번째 질문
        print(f"\n질문: {query}\n")
        print("응답:")
        full_response = ''

        # 스트리밍 응답 처리
        for response_chunk in client.chat(repo_name=repo_url, query=query):
            print(response_chunk, end='', flush=True)
            full_response += response_chunk

        # 두 번째 질문: 이전 응답을 한국어로 번역 요청
        print(f"\n\n질문: translate your answer to korean\n")
        print("응답:")
        chat_history = [
            {"role": "user", "content": query},
            {"role": "assistant", "content": full_response}
        ]

        # 번역 요청 스트리밍 처리
        for response_chunk in client.chat(repo_name=repo_url, query="translate your answer to korean", chat_history=chat_history):
            print(response_chunk, end='', flush=True)
        
        '''
    except Exception as e:
        logger.error(f"채팅 실패: {str(e)}") 
        

if __name__ == "__main__":
    asyncio.run(main())