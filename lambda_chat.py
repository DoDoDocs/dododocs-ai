import json
from aws_lambda_powertools import Logger
from ktb_chatbot import codebase_chat

# 로깅 설정
logger = Logger(service="chat_service")


def lambda_handler(event, context):
    try:
        # API Gateway로부터 요청 데이터 추출
        body = json.loads(event['body'])
        repo_url = body['repo_url']
        query = body['query']
        chat_history = body.get('chat_history', None)
        stream = body.get('stream', False)

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
            response = codebase_chat(
                query,
                repo_url,
                formatted_chat_history,
                stream
            )
        else:
            response = codebase_chat(
                query,
                repo_url,
                chat_history,
                stream
            )

        if stream:
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/plain'},
                'body': response
            }
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
