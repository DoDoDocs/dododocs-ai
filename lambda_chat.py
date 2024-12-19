# lambda_chat.py
import json
import asyncio
import uuid
from aws_lambda_powertools import Logger
from ktb_chatbot import codebase_chat

# 로깅 설정
logger = Logger(service="chat_service")


async def generate_sse(query, repo_url, chat_history, stream):
    response = codebase_chat(
        query,
        repo_url,
        chat_history,
        stream
    )
    if stream:
        for chunk in response:
            yield chunk
    else:
        yield response


def lambda_handler(event, context):
    try:
        # API Gateway로부터 요청 데이터 추출
        body = json.loads(event['body'])
        repo_url = body['repo_url']
        query = body['query']
        chat_history = body.get('chat_history', None)
        stream = body.get('stream', False)

        # 경로 파라미터에서 식별자 추출
        stream_id = event['pathParameters'].get('id', str(uuid.uuid4()))

        if not query.strip():
            return {
                'statusCode': 400,
                'body': json.dumps({'detail': 'Query cannot be empty'})
            }

        # chat_history가 딕셔너리로 주어졌을 때 변환
        if chat_history:
            formatted_chat_history = []
            for item in chat_history:
                formatted_chat_history.append(
                    {"role": "user", "content": item["question"]})
                formatted_chat_history.append(
                    {"role": "assistant", "content": item["answer"]})

            sse_generator = generate_sse(
                query,
                repo_url,
                formatted_chat_history,
                stream
            )
        else:
            sse_generator = generate_sse(
                query,
                repo_url,
                chat_history,
                stream
            )

        # 동적 URL 생성
        dynamic_url = f"https://{event['requestContext']['domainName']}/{
            event['requestContext']['stage']}/stream/{stream_id}"

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Stream-URL": dynamic_url  # 클라이언트에게 동적 URL 전달
            },
            "body": "".join(asyncio.run(sse_generator))
        }

    except Exception as error:
        logger.error(f"채팅 오류: {str(error)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'answer': f"Error: {str(error)}"}, ensure_ascii=False)
        }
