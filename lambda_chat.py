# flask_chat.py
from flask import Flask, Response, stream_with_context, request, jsonify
import os
from aws_lambda_powertools import Logger
from ktb_settings import *
from ktb_chatbot import *
from ktb_func import *
from flask_cors import CORS
import json
import time


app = Flask(__name__)

# 로깅 설정
logger = Logger(service="chat_service")

origins = [
    "http://localhost:8080",
    "http://localhost:3000",
    "https://dododocs.com",
    "https://dododocs.com/api",
]

# CORS(app, resources={r"/chat": {"origins": "*"}},
#      supports_credentials=True)
CORS(app, resources={r"/chat": {"origins": origins}},
     supports_credentials=True)


def is_christmas():
    result = ""
    result += ('\n'.join
               ([''.join
                 ([('Merry Christmas '[(x-y) % 8]
                    if ((x*0.05)**2+(y*0.1)**2-1)
                     ** 3 - (x*0.05)**2*(y*0.1)
                     ** 3 <= 0 else ' ')
                  for x in range(-30, 30)])
                for y in range(15, -15, -1)]))
    result += "Merry Christmas"
    return result


@app.route('/chat', methods=['POST', 'GET'])
def chat():
    """채팅 엔드포인트"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            if not data or not data.get('query'):
                return jsonify({"detail": "Query cannot be empty"}), 400
            repo_url = data.get('repo_url')
            query = data.get('query')
            chat_history = data.get('chat_history')
            stream = data.get('stream', True)
        elif request.method == 'GET':
            query = request.args.get('query')
            repo_url = request.args.get('repo_url')
            chat_history = request.args.get('chat_history')
            stream = request.args.get('stream', True)
            if not query:
                return jsonify({"detail": "Query cannot be empty"}), 400
            if chat_history:
                try:
                    chat_history = json.loads(chat_history)
                except json.JSONDecodeError:
                    return jsonify({"detail": "Invalid chat_history format"}), 400
        else:
            return jsonify({"detail": "Method not allowed"}), 405

        logger.error(f"Received data: {data}")

        # 크리스마스 이스터에그
        if query == "!christmas":
            return json.dumps(is_christmas()), 200

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
                    json_data = json.dumps(
                        {'answer': response}, ensure_ascii=False)
                    yield f"data: {json_data}\n\n".encode('utf-8')
                else:
                    chunk_buffer = ""
                    for chunk in response:
                        chunk_buffer += chunk  # .replace('\n', '<br/>')
                        # chunk_buffer += chunk
                        if len(chunk_buffer) > 200:
                            logger.info(f"chunk_buffer: {chunk_buffer}")
                            json_data = json.dumps(
                                {'AI asnwer': chunk_buffer}, ensure_ascii=False)
                            yield f"{json_data}\n\n".encode('utf-8')
                            time.sleep(1)
                            chunk_buffer = ""
                    if chunk_buffer:
                        logger.info(f"chunk_buffer: {chunk_buffer}")
                        json_data = json.dumps(
                            {'AI asnwer': chunk_buffer}, ensure_ascii=False)
                        yield f"{json_data}\n\n".encode('utf-8')
            return Response(stream_with_context(stream_response()), content_type='text/event-stream')
        else:
            if isinstance(response, str):
                return json.dumps({'AI answer': response}), 200
            else:
                full_response = "".join(response)
                logger.info(f"response: {full_response}")
                return json.dumps({'AI answer': full_response}), 200

    except Exception as error:
        logger.error(f"채팅 오류: {str(error)}", exc_info=True)
        return jsonify({'answer': f"Error: {str(error)}", 'statusCode': 500}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5001)), debug=True)
