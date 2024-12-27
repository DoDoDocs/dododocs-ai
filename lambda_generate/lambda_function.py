import json
import logging
import asyncio
import os
from typing import Tuple
import boto3
import requests
import time


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
        if java_categories:
            docs_task = asyncio.create_task(process_docs(
                java_categories, doc_dir, docs_key, korean, clone_dir, metadata))
            tasks.append(docs_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        readme_path, docs_dir = results if len(
            results) == 2 else (results[0], None)

        if not docs_dir or not readme_path:
            logger.error("문서 또는 README 생성 실패")
            raise Exception("문서 또는 README 생성 실패")

        all_tasks_successful = all(not isinstance(
            result, Exception) for result in results)
        if all_tasks_successful:
            if os.path.exists(os.path.join(clone_dir, "dododocs")):
                await add_data_to_db(f"{user_name}_{repo_name}_generated", f"{clone_dir}/dododocs", [".md"])
            await add_data_to_db(f"{user_name}_{repo_name}_generated", f"{clone_dir}")
        else:
            logger.error(f"Task failed, not adding data to db")

    except Exception as e:
        logger.error(f"문서 및 README 생성 오류: {str(e)}, problem: {e}")


async def process_docs(directory_path: dict[str, list], output_directory: str, docs_key: str, korean: bool, clone_dir: str, metadata: dict = None) -> bool:
    """문서 생성 및 요약 처리"""
    try:
        await doc_processor.generate_docs(directory_path, output_directory, korean, clone_dir)
        await doc_processor.summarize_docs_async_nogenerate(output_directory, korean)
        # await doc_processor.summarize_docs_async(output_directory, korean)
        create_zip(output_directory, "/tmp/Docs.zip")
        await upload_to_s3(BUCKET_NAME, "/tmp/Docs.zip", "result/"+docs_key, metadata)
        return True
    except Exception as doc_error:
        logger.error(f"문서 생성 중 오류 발생: {str(doc_error)}")
        return False


def prepare_repository(repo_url: str, s3_key: str) -> Tuple[str, str, str, str, str]:
    """저장소 준비: URL 파싱, S3 다운로드, 압축 해제"""
    try:
        user_name, repo_name, source_path = parse_repo_url(repo_url)
        current_directory = '/tmp'
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
            logger.error(f"Error renaming folder: {str(e)}")
            raise Exception(f"Error renaming folder: {str(e)}")

        return repo_path, clone_dir, repo_name, user_name, source_path

    except Exception as e:
        logger.error(f"Repository preparation failed: {str(e)}")
        raise Exception(f"Repository preparation failed: {str(e)}")


def clear_tmp_directory():
    """/tmp 디렉토리 내의 모든 파일을 삭제합니다."""
    tmp_dir = "/tmp"
    try:
        if os.path.exists(tmp_dir):
            for filename in os.listdir(tmp_dir):
                file_path = os.path.join(tmp_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error(
                        f"Error deleting file/directory {file_path}: {str(e)}")
            logger.info(f"Successfully cleared /tmp directory")
    except Exception as e:
        logger.error(f"Error clearing /tmp directory: {str(e)}")


async def generate(request):
    """문서 및 README 생성 작업 수행"""
    # attempt = 0
    try:
        print(f"request: {request}")
        repo_dir, clone_dir, repo_name, user_name, source_path = prepare_repository(
            request['repo_url'],
            request['s3_key']
        )
        logger.info(f"repo_dir: {repo_dir}, type: {type(repo_dir)}")
        logger.info(f"clone_dir: {clone_dir}, type: {type(clone_dir)}")
        logger.info(f"repo_name: {repo_name}, type: {type(repo_name)}")
        logger.info(f"user_name: {user_name}, type: {type(user_name)}")
        logger.info(f"branch_name: {source_path}, type: {type(source_path)}")

        java_files_path = file_utils.find_files(clone_dir, (".java",))
        has_java_files = len(java_files_path) > 0
        logger.info(f"has_java_files: {has_java_files}")
        metadata = {
            'repo_url': request['repo_url']
        }
        tasks = []
        tasks.append(asyncio.create_task(
            perform_full_generation(
                request['repo_url'], clone_dir, user_name, repo_name, request['readme_key'],
                request['docs_key'], request['include_test'], request['korean'], request['blocks'], metadata)
        ))

        file_types = [ft for ft in SRC_FILE_NAMES if ft != '.md']
        logger.info(f"source_path: {clone_dir}/{source_path}")

        # tasks.append(asyncio.create_task(
        #     add_data_to_db(f"{user_name}_{repo_name}_source", f"{
        #                    clone_dir}", file_types)
        # ))
        await asyncio.gather(*tasks)

        # source_db_task = asyncio.create_task(
        #     add_data_to_db(f"{repo_name}_source", f"{
        #                    clone_dir}/{source_path}", file_types)
        # )
        # tasks.append(source_db_task)
        # await asyncio.gather(*tasks)
        await add_data_to_db(f"{user_name}_{repo_name}_source", f"{clone_dir}/{source_path}", file_types)

        return True
    except Exception as e:
        logger.error(f"generate 문서 및 README 생성 오류: {str(e)}")
        return False


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
        include_test = metadata.get('include_test', 'false').lower() == 'true'
        # include_test = 'false'
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
        MAX_RETRIES = 0
        # attempt = 0
        asyncio.run(generate(request))
        # 챗봇 준비 완료 백엔드 호출 함수 생성
        url = "https://dododocs.com/api/register/status/chatbot"
        body = {
            "repoUrl": repo_url,
            "chatbotCompleted": True
        }
        # else:
        #     while attempt < MAX_RETRIES:
        #         result = asyncio.run(generate(request))
        #         attempt += 1
        #         if result:
        #             break
        #         time.sleep(1)
        #         url = "https://dododocs.com/api/register/status/chatbot"
        #         body = {
        #             "repoUrl": repo_url,
        #             "chatbotCompleted": True
        #         }
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
    finally:
        clear_tmp_directory()
