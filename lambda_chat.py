# flask_chat.py
from flask import Flask, Response, stream_with_context, request, jsonify
import os
from aws_lambda_powertools import Logger
from ktb_settings import *
from ktb_chatbot import *
from ktb_func import *
from flask_cors import CORS
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
        data = request.get_json()
        logger.error(f"Received data: {data}")
        if not data or not data.get('query'):
            return jsonify({"detail": "Query cannot be empty"}), 400

        repo_url = data.get('repo_url')
        query = data.get('query')
        chat_history = data.get('chat_history')
        stream = data.get('stream', True)

        # 크리스마스 이스터에그
        if query == "!christmas":
            return jsonify({'answer': is_christmas()}), 200

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
        test_generator = {
            "test1",
            "test2",
            "test3",
            "test4",
            "test5",
        }
        # if stream:
        #     test_generator = ["test1", "test2", "test3", "test4", "test5"]

        #     def stream_response():
        #         for item in test_generator:
        #             yield f"data: {json.dumps({'answer': item})}\n\n".encode('utf-8')
        #             time.sleep(0.5)
        #     return Response(stream_with_context(stream_response()), content_type='text/event-stream')
        # else:
        #     if isinstance(response, str):
        #         return jsonify({'answer': response}), 200
        #     else:
        #         full_response = "".join(response)
        #         logger.info(f"response: {full_response}")
        #         return jsonify({'answer': full_response}), 200

        if stream:
            def stream_response():
                if isinstance(response, str):
                    yield f"{response}".encode('utf-8')
                else:
                    chunk_buffer = ""
                    for chunk in response:
                        chunk_buffer += chunk
                        if len(chunk_buffer) > 50:
                            logger.info(f"chunk_buffer: {chunk_buffer}")
                            yield f"data: {chunk_buffer}\n\n".encode('utf-8')
                            time.sleep(0.5)
                            chunk_buffer = ""
                    yield f"data: {chunk_buffer}\n\n".encode('utf-8')
            return Response(stream_with_context(stream_response()), content_type='text/event-stream')
        else:
            logger.info(f"response: {response}")
            return jsonify({'answer': response}), 200

    except Exception as error:
        logger.error(f"채팅 오류: {str(error)}", exc_info=True)
        return jsonify({'answer': f"Error: {str(error)}", 'statusCode': 500}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5001)), debug=True)
