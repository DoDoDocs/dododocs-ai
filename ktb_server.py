from fastapi import FastAPI, HTTPException, status, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple
import os

from ktb_document_processor import DocumentProcessor
from ktb_api_client import APIClient
from ktb_utils import FileUtils
from ktb_settings import *
from ktb_chatbot import *
from ktb_func import *


origins = [
    "http://localhost:8080",
    "http://localhost:3000"
]

# 로깅 설정
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],  # 모든 HTTP 메서드 허용
#     allow_headers=["*"],  # 모든 헤더 허용
# )

# API 클라이언트 및 문서 프로세서 초기화
api_client = APIClient()
doc_processor = DocumentProcessor(api_client)
file_utils = FileUtils()


class DocRequest(BaseModel):
    repo_url: str
    s3_path: str
    include_test: bool = False
    korean: bool = False
    blocks: List[str] = [
        "OVERVIEW_BLOCK",
        "STRUCTURE_BLOCK",
        "START_BLOCK",
        "MOTIVATION_BLOCK",
        "DEMO_BLOCK",
        "DEPLOYMENT_BLOCK",
        "CONTRIBUTORS_BLOCK",
        "FAQ_BLOCK",
        "PERFORMANCE_BLOCK"
    ]


class ChatRequest(BaseModel):
    repo_url: str
    query: str
    chat_history: Optional[List[Dict[str, Any]]] = None
    stream: bool = False


def cleanup(repo_zip: str, clone_dir: str, doc_zip: str):
    """임시 파일 및 디렉토리 정리"""
    try:
        # repo_zip 파일 삭제
        if repo_zip and os.path.exists(repo_zip):
            os.remove(repo_zip)
            print(f"Removed repo zip file: {repo_zip}")

        # ZIP 파일 삭제
        if doc_zip and os.path.exists(doc_zip):
            os.remove(doc_zip)
            print(f"Removed zip file: {doc_zip}")

        # 클론 디렉토리 삭제
        if clone_dir and os.path.exists(clone_dir):
            shutil.rmtree(clone_dir)
            print(f"Removed clone directory: {clone_dir}")

    except Exception as e:
        print(f"Cleanup failed: {str(e)}")


def prepare_repository(repo_url: str, s3_key: str) -> Tuple[str, str, str, str, str]:
    """저장소 준비: URL 파싱, S3 다운로드, 압축 해제"""
    try:
        # 저장소 경로 파싱
        print("Repository preparation started")
        user_name, repo_name, source_path = parse_repo_url(repo_url)
        current_directory = os.getcwd()
        repo_path = os.path.join(current_directory, f"{repo_name}.zip")
        clone_dir = os.path.join(current_directory, f"{user_name}_{repo_name}")
        print(f"repo_path: {repo_path}")
        print(f"clone_dir: {clone_dir}")
        download_zip_from_s3(BUCKET_NAME, s3_key, repo_path)
        extract_zip(repo_path, clone_dir)

        logger.info(f"Repository extraction completed: {clone_dir}")

        # 폴더 이름 변경
        try:
            extracted_folder_name = os.listdir(clone_dir)[0]
            logger.info(f"extracted_folder_name: {extracted_folder_name}")
            extracted_folder_path = os.path.join(
                clone_dir, extracted_folder_name)
            new_folder_path = os.path.join(clone_dir, source_path)
            logger.info(f"new_folder_path: {new_folder_path}")
            os.rename(extracted_folder_path, new_folder_path)
        except Exception as e:
            print(f"Error renaming folder: {str(e)}")
            raise Exception(f"Error renaming folder: {str(e)}")

        return repo_path, clone_dir, repo_name, user_name, source_path

    except Exception as e:
        print(f"Repository preparation failed: {str(e)}")
        raise Exception(f"Repository preparation failed: {str(e)}")


async def process_docs(directory_path: dict[str, list], output_directory: str, 
                    docs_key: str, korean: bool, clone_dir: str, metadata: dict = None) -> bool:
    """문서 생성 및 요약 처리"""
    try:
        await doc_processor.generate_docs(directory_path, output_directory, korean, clone_dir)
        await doc_processor.summarize_docs_async_nogenerate(output_directory)
        create_zip(output_directory, "./Docs.zip")
        await upload_to_s3(BUCKET_NAME, "./Docs.zip", docs_key, metadata)
        return True
    except Exception as doc_error:
        print(f"문서 생성 중 오류 발생: {str(doc_error)}")
        return False

@timer
async def perform_full_generation(repo_url, clone_dir, user_name, repo_name, readme_key,
                                docs_key, include_test, korean, blocks, metadata):
    """문서 및 README 생성 작업을 백그라운드에서 수행"""
    try:
        java_files_path = file_utils.find_files(clone_dir, (".java",))
        java_categories = check_service_annotation(
            java_files_path, include_test)

        tasks = []
        readme_task = asyncio.create_task(doc_processor.process_readme(
            repo_url, clone_dir, readme_key, korean, blocks, metadata))
        tasks.append(readme_task)

        doc_dir = os.path.join(clone_dir, "dododocs")
        docs_task = asyncio.create_task(process_docs(
            java_categories, doc_dir, docs_key, korean, clone_dir, metadata))
        tasks.append(docs_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        readme_path, docs_dir = results if len(
            results) == 2 else (results[0], None)

        if not docs_dir or not readme_path:
            print("문서 또는 README 생성 실패")
            raise Exception("문서 또는 README 생성 실패")

        all_tasks_successful = all(not isinstance(
            result, Exception) for result in results)
        # if all_tasks_successful:
        #     if os.path.exists(os.path.join(clone_dir, "dododocs")):
        #         await add_data_to_db(f"{user_name}_{repo_name}_generated", f"{clone_dir}/dododocs", [".md"])
        #     await add_data_to_db(f"{user_name}_{repo_name}_generated", f"{clone_dir}")
        # else:
        #     print(f"Task failed, not adding data to db")

    except Exception as e:
        print(f"문서 및 README 생성 오류: {str(e)}, problem: {e}")


async def perform_tasks_and_cleanup(tasks, cleanup_args, db_name, clone_dir):
    """백그라운드 작업을 수행하고 완료되면 cleanup 실행"""
    await asyncio.gather(*tasks)  # 모든 백그라운드 작업이 완료될 때까지 대기
    print(f"add_data_to_db 완료: {db_name}, {clone_dir}")
    await async_cleanup(*cleanup_args)  # cleanup 실행

@async_timer
@app.post("/generate")
async def generate(request: DocRequest, background_tasks: BackgroundTasks):
    """문서 및 README 생성 엔드포인트"""
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            # 1. Git 저장소 준비
            repo_dir, clone_dir, repo_name, user_name, source_path = prepare_repository(
                request.repo_url,
                request.s3_path
            )
            # S3 키 생성
            readme_s3_key = f"{user_name}_{repo_name}_README.md"
            docs_s3_key = f"{user_name}_{repo_name}_DOCS.zip"
            metadata = {
                'repo_url': request.repo_url
            }
            # 백그라운드 작업 생성
            tasks = []
            readme_key = f"{user_name}_{repo_name}_README.md"
            docs_key = f"{user_name}_{repo_name}_DOCS.zip"
            tasks.append(asyncio.create_task(
                perform_full_generation(
                    request.repo_url, clone_dir, user_name, repo_name, readme_key,
                    docs_key, request.include_test, request.korean, request.blocks, metadata)
            ))
            response = {"readme_s3_key": readme_s3_key,
                        "docs_s3_key": docs_s3_key}

            file_types = [ft for ft in SRC_FILE_NAMES if ft != '.md']
            print(f"source_path: {clone_dir}/{source_path}")

            await asyncio.gather(*tasks)
            # await add_data_to_db(f"{user_name}_{repo_name}_source", f"{clone_dir}/{source_path}", file_types)


            return response

        except Exception as e:
            attempt += 1
            print(f"문서 및 README 생성 오류 (시도 {attempt}/{MAX_RETRIES}): {str(e)}")
            if attempt >= MAX_RETRIES:
                print("최대 재시도 횟수에 도달했습니다. 작업을 중단합니다.")
            else:
                logger.info(f"{RETRY_DELAY}초 후에 재시도합니다...")
                await asyncio.sleep(RETRY_DELAY)  # 재시도 간격 대기
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"문서 및 README 생성 오류: {str(e)}"
    )


@app.post("/chat")
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
            return StreamingResponse(
                response,
                media_type="text/plain"
            )
        else:
            return {"answer": response}

    except Exception as error:
        print(f"채팅 오류: {str(error)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(error)}"
        )


@app.get("/ping")
async def ping():
    try:
        return JSONResponse(status_code=200, content={"message": "pong"})
    except Exception as e:
        # 오류 발생 시 예외 처리
        raise HTTPException(
            status_code=500,
            detail=f"오류 발생: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(
        "ktb_server:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        workers=1
    )
