from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional, List, Dict, Any
import os
from aws_lambda_powertools import Logger
import json
from ktb_settings import *
from ktb_chatbot import *
from ktb_func import *


origins = [
    "http://localhost:8080",
    "http://localhost:3000"
]

# 로깅 설정
logger = Logger(service="chat_service")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)


class ChatRequest(BaseModel):
    repo_url: str
    query: str
    chat_history: Optional[List[Dict[str, Any]]] = None
    stream: bool = True


@app.post('/chat')
async def chat(request: ChatRequest):
    """채팅 엔드포인트"""
    try:
        if not request.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )

        # chat_history가 딕셔너리로 주어졌을 때 변환
        if request.chat_history:
            chat_history = []
            for item in request.chat_history:
                chat_history.append(
                    {"role": "user", "content": item["question"]})
                chat_history.append(
                    {"role": "assistant", "content": item["answer"]})
            response = codebase_chat(
                request.query,
                request.repo_url,
                chat_history,
                request.stream
            )
        else:
            response = codebase_chat(
                request.query,
                request.repo_url,
                request.chat_history,
                request.stream
            )

        if request.stream:
            # async def stream_response():
            #     if isinstance(response, str):
            #         yield f"data: {{\"message\": \"{response}\"}}\n\n".encode('utf-8')
            #     else:
            #         async for chunk in response:
            #             yield f"data: {{\"message\": \"{chunk}\"}}\n\n".encode('utf-8')
            return StreamingResponse(
                response,
                media_type="text/event-stream"
            )
        else:
            return {
                'statusCode': 200,
                'body': json.dumps({'answer': response})
            }

    except Exception as error:
        logger.error(f"채팅 오류: {str(error)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'answer': f"Error: {str(error)}"})
        }


if __name__ == "__main__":
    uvicorn.run(
        "lambda_chat:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        workers=1
    )
