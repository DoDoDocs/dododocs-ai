import json
import logging
import asyncio
import os
from typing import Tuple

from ktb_document_processor import DocumentProcessor
from ktb_api_client import APIClient
from ktb_utils import FileUtils, ImageProcessor
from ktb_settings import *
from ktb_chatbot import *
from ktb_func import *

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# API 클라이언트 및 문서 프로세서 초기화
api_client = APIClient(os.getenv('OPENAI_API_KEY'))
doc_processor = DocumentProcessor(api_client)
file_utils = FileUtils()
image_processor = ImageProcessor()


async def perform_full_generation(repo_url, clone_dir, repo_name, user_name, include_test, korean, blocks):
    """문서 및 README 생성 작업을 백그라운드에서 수행"""
    try:
        java_files_path = file_utils.find_files(clone_dir, (".java",))
        java_categories = check_service_annotation(
            java_files_path, include_test)

        tasks = []
        readme_task = asyncio.create_task(doc_processor.process_readme(
            repo_url, clone_dir, user_name, repo_name, korean, blocks))
        tasks.append(readme_task)

        doc_dir = os.path.join(clone_dir, "dododocs")
        if java_categories:
            docs_task = asyncio.create_task(process_docs(
                java_categories, doc_dir, user_name, repo_name, korean))
            tasks.append(docs_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        readme_path, docs_dir = results if len(
            results) == 2 else (results[0], None)

        if not docs_dir or not readme_path:
            logger.error("문서 또는 README 생성 실패")
            raise Exception("문서 또는 README 생성 실패")

        await add_data_to_db(f"{repo_name}_generated", clone_dir, [".md"])

    except Exception as e:
        logger.error(f"문서 및 README 생성 오류: {str(e)}")


async def process_docs(directory_path: dict[str, list], output_directory: str, user_name: str, repo_name: str, korean: bool) -> bool:
    """문서 생성 및 요약 처리"""
    try:
        await doc_processor.generate_docs(directory_path, output_directory, korean)
        await doc_processor.summarize_docs_async(output_directory, korean)
        create_zip(output_directory, "Docs.zip")
        await upload_to_s3(BUCKET_NAME, "Docs.zip", f"{user_name}_{repo_name}_DOCS.zip")
        return True
    except Exception as doc_error:
        logger.error(f"문서 생성 중 오류 발생: {str(doc_error)}")
        return False


async def perform_readme_only_generation(repo_url, clone_dir, repo_name, user_name, korean, blocks):
    """README 생성 작업만 백그라운드에서 수행"""
    try:
        readme = await doc_processor.process_readme(repo_url, clone_dir, user_name, repo_name, korean, blocks)
        if not readme:
            logger.error("README 생성 실패")
            raise Exception("README 생성 실패")

        await add_data_to_db(f"{repo_name}_generated", clone_dir, [".md"])

    except Exception as e:
        logger.error(f"README 생성 오류: {str(e)}")


async def perform_tasks_and_cleanup(tasks, cleanup_args, db_name, clone_dir):
    """백그라운드 작업을 수행하고 완료되면 cleanup 실행"""
    await asyncio.gather(*tasks)
    logger.info(f"add_data_to_db 완료: {db_name}, {clone_dir}")
    await async_cleanup(*cleanup_args)


async def prepare_repository(repo_url: str, s3_path: str) -> Tuple[str, str, str, str]:
    """저장소 준비: URL 파싱, S3 다운로드, 압축 해제"""
    try:
        repo_name, user_name = parse_repo_url(repo_url)
        current_directory = '/tmp'
        repo_path = os.path.join(current_directory, f"{repo_name}.zip")
        clone_dir = os.path.join(current_directory, f"{user_name}_{repo_name}")

        download_zip_from_s3(BUCKET_NAME, s3_path, repo_path)
        while not os.path.exists(repo_path):
            await asyncio.sleep(0.1)

        extract_zip(repo_path, clone_dir)
        while not os.path.exists(clone_dir) or not os.listdir(clone_dir):
            await asyncio.sleep(0.1)

        logger.info(f"Repository extraction completed: {clone_dir}")

        return repo_path, clone_dir, repo_name, user_name

    except Exception as e:
        logger.error(f"Repository preparation failed: {str(e)}")
        raise Exception(f"Repository preparation failed: {str(e)}")


def lambda_handler(event, context):
    """AWS Lambda 핸들러"""
    try:
        request = json.loads(event['body'])
        asyncio.run(generate(request))
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "문서 생성 작업이 시작되었습니다."})
        }
    except Exception as e:
        logger.error(f"문서 생성 오류: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"문서 생성 오류: {str(e)}"})
        }


async def generate(request):
    """문서 및 README 생성 작업 수행"""
    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            repo_dir, clone_dir, repo_name, user_name = await prepare_repository(
                request['repo_url'],
                request['s3_path']
            )
            java_files_path = file_utils.find_files(clone_dir, (".java",))
            has_java_files = len(java_files_path) > 0
            logger.info(f"has_java_files: {has_java_files}")

            tasks = []
            if has_java_files:
                tasks.append(asyncio.create_task(
                    perform_full_generation(
                        request['repo_url'], clone_dir, repo_name, user_name, request['include_test'], request['korean'], request['blocks'])
                ))
            else:
                tasks.append(asyncio.create_task(
                    perform_readme_only_generation(
                        repo_dir, clone_dir, repo_name, user_name, request['korean'], request['blocks'])
                ))

            file_types = [ft for ft in SRC_FILE_NAMES if ft != '.md']
            logger.info(f"total files : {len(file_types)}")
            source_db_task = asyncio.create_task(
                add_data_to_db(f"{repo_name}_source", clone_dir, file_types)
            )
            tasks.append(source_db_task)

            await perform_tasks_and_cleanup(tasks, (
                repo_dir, clone_dir, "Docs.zip"), f"{repo_name}_generated", clone_dir)

            return

        except Exception as e:
            attempt += 1
            logger.error(f"문서 및 README 생성 오류 (시도 {
                         attempt}/{MAX_RETRIES}): {str(e)}")
            if attempt >= MAX_RETRIES:
                logger.error("최대 재시도 횟수에 도달했습니다. 작업을 중단합니다.")
                break
            else:
                logger.info(f"{RETRY_DELAY}초 후에 재시도합니다...")
                await asyncio.sleep(RETRY_DELAY)
    logger.error(f"문서 및 README 생성 오류: {str(e)}")
