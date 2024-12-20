# flask_chat.py
from flask import Flask, Response, stream_with_context, request, jsonify
import time
import random
import os
from aws_lambda_powertools import Logger
import json
from ktb_settings import *
from ktb_chatbot import *
from ktb_func import *
from flask_cors import CORS

app = Flask(__name__)

# 로깅 설정
logger = Logger(service="chat_service")

origins = [
    "http://localhost:8080",
    "http://localhost:3000"
]

CORS(app, resources={r"/chat": {"origins": origins}},
     supports_credentials=True)


@app.route('/chat', methods=['POST'])
def chat():
    """채팅 엔드포인트"""
    try:
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({"detail": "Query cannot be empty"}), 400

        repo_url = data.get('repo_url')
        query = data.get('query')
        chat_history = data.get('chat_history')
        stream = data.get('stream', True)

        if chat_history:
            chat_history_list = []
            for item in chat_history:
                chat_history_list.append(
                    {"role": "user", "content": item["question"]})
                chat_history_list.append(
                    {"role": "assistant", "content": item["answer"]})
            response = codebase_chat(
                query=query,
                repo_url=repo_url,
                chat_history=chat_history_list,
                stream=stream
            )
        else:
            response = codebase_chat(
                query=query,
                repo_url=repo_url,
                chat_history=chat_history,
                stream=stream
            )

        if stream:
            def stream_response():
                if isinstance(response, str):
                    yield f"data: {{\"message\": \"{response}\"}}\n\n".encode('utf-8')
                else:
                    for chunk in response:
                        yield f"data: {{\"message\": \"{chunk}\"}}\n\n".encode('utf-8')
            return Response(stream_with_context(stream_response()), content_type='text/event-stream')
        else:
            return jsonify({'answer': response}), 200

    except Exception as error:
        logger.error(f"채팅 오류: {str(error)}", exc_info=True)
        return jsonify({'answer': f"Error: {str(error)}", 'statusCode': 500}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5001)), debug=True)
