import json
import logging
import asyncio
import os
from typing import Tuple
import boto3
import requests

from ktb_document_processor import DocumentProcessor
from ktb_api_client import APIClient
from ktb_utils import FileUtils
from ktb_settings import *
from ktb_chatbot import *
from ktb_func import *

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# API 클라이언트 및 문서 프로세서 초기화
api_client = APIClient()
doc_processor = DocumentProcessor(api_client)
file_utils = FileUtils()

s3 = boto3.client('s3')


async def perform_full_generation(repo_url, clone_dir, repo_name, readme_key, docs_key, include_test, korean, blocks, metadata):
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
        if java_categories:
            docs_task = asyncio.create_task(process_docs(
                java_categories, doc_dir, docs_key, korean, metadata))
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


async def process_docs(directory_path: dict[str, list], output_directory: str, docs_key: str, korean: bool, metadata: dict = None) -> bool:
    """문서 생성 및 요약 처리"""
    try:
        await doc_processor.generate_docs(directory_path, output_directory, korean)
        await doc_processor.summarize_docs_async_nogenerate(output_directory, korean)
        # await doc_processor.summarize_docs_async(output_directory, korean)
        create_zip(output_directory, "/tmp/Docs.zip")
        await upload_to_s3(BUCKET_NAME, "/tmp/Docs.zip", "result/"+docs_key, metadata)
        return True
    except Exception as doc_error:
        logger.error(f"문서 생성 중 오류 발생: {str(doc_error)}")
        return False


async def perform_tasks_and_cleanup(tasks, cleanup_args, db_name, clone_dir):
    """백그라운드 작업을 수행하고 완료되면 cleanup 실행"""
    await asyncio.gather(*tasks)
    await async_cleanup(*cleanup_args)


def prepare_repository(repo_url: str, s3_key: str) -> Tuple[str, str, str, str]:
    """저장소 준비: URL 파싱, S3 다운로드, 압축 해제"""
    try:
        user_name, repo_name = parse_repo_url(repo_url)
        current_directory = '/tmp'
        repo_path = os.path.join(current_directory, f"{repo_name}.zip")
        clone_dir = os.path.join(current_directory, f"{user_name}_{repo_name}")
        print(f"repo_path: {repo_path}")
        print(f"clone_dir: {clone_dir}")
        download_zip_from_s3(BUCKET_NAME, s3_key, repo_path)
        extract_zip(repo_path, clone_dir)

        logger.info(f"Repository extraction completed: {clone_dir}")

        return repo_path, clone_dir, repo_name, user_name

    except Exception as e:
        logger.error(f"Repository preparation failed: {str(e)}")
        raise Exception(f"Repository preparation failed: {str(e)}")


async def generate(request):
    """문서 및 README 생성 작업 수행"""
    # attempt = 0
    try:
        repo_dir, clone_dir, repo_name, user_name = prepare_repository(
            request['repo_url'],
            request['s3_key']
        )
        java_files_path = file_utils.find_files(clone_dir, (".java",))
        has_java_files = len(java_files_path) > 0
        logger.info(f"has_java_files: {has_java_files}")
        metadata = {
            'repo_url': request['repo_url']
        }
        tasks = []
        tasks.append(asyncio.create_task(
            perform_full_generation(
                request['repo_url'], clone_dir, repo_name, request['readme_key'], request['docs_key'], request['include_test'], request['korean'], request['blocks'], metadata)
        ))

        file_types = [ft for ft in SRC_FILE_NAMES if ft != '.md']
        logger.info(f"total files : {len(file_types)}")
        source_db_task = asyncio.create_task(
            add_data_to_db(f"{repo_name}_source", clone_dir, file_types)
        )
        tasks.append(source_db_task)

        await perform_tasks_and_cleanup(tasks, (
            repo_dir, clone_dir, "/tmp/Docs.zip"), f"{repo_name}_generated", clone_dir)
    except Exception as e:
        logger.error(f"문서 및 README 생성 오류: {str(e)}")


def lambda_handler(event, context):
    """AWS Lambda 핸들러"""
    try:
        # S3 이벤트에서 정보 추출
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        s3_key = event['Records'][0]['s3']['object']['key']

        # S3 객체 메타데이터 가져오기
        response = s3.head_object(Bucket=bucket_name, Key=s3_key)
        metadata = response.get('Metadata', {})
        print(f"bucket_name: {bucket_name}")
        print(f"s3_key: {s3_key}")
        # 메타데이터에서 필요한 값 추출
        repo_url = metadata.get('repo_url')
        readme_key = metadata.get('readme_key')
        docs_key = metadata.get('docs_key')
        include_test = 'false'
        korean = metadata.get('korean', 'false').lower() == 'true'

        blocks = [
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

        if not repo_url or not readme_key or not docs_key:
            logger.error(
                "repo_url or readme_key or docs_key not found in metadata")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "repo_url or readme_key or docs_key not found in metadata"})
            }

        request = {
            'repo_url': repo_url,
            'readme_key': readme_key,
            'docs_key': docs_key,
            'include_test': include_test,
            'korean': korean,
            'blocks': blocks,
            's3_key': s3_key
        }
        asyncio.run(generate(request))

        # 챗봇 준비 완료 백엔드 호출 함수 생성
        url = "https://dododocs.com/api/register/status/chatbot"
        body = {
            "repoUrl": repo_url,
            "chatbotCompleted": True
        }

        response = requests.put(url, json=body)
        logger.info(f"response: {response}, response.status_code: {
                    response.status_code}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "All generation completed"})
        }
    except Exception as e:
        logger.error(f"문서 생성 오류: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"문서 생성 오류: {str(e)}"})
        }
