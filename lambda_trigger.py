import json
import boto3
import os
from pydantic import BaseModel
from typing import List

# Boto3 클라이언트 생성
lambda_client = boto3.client('lambda',
                             region_name='ap-northeast-2'
                             )


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


def parse_repo_url(repo_url):
    """Extract user and repo name from the repo URL"""
    # Example implementation, adjust based on actual URL structure
    parts = repo_url.rstrip('/').split('/')
    user_name = parts[-3]
    repo_with_branch = parts[-2]+'_'+parts[-1]
    return user_name, repo_with_branch


def lambda_handler(event, context):
    # 호출할 Lambda 함수의 이름
    target_lambda_name = os.getenv('TARGET_LAMBDA_NAME')

    # DocRequest 형식의 페이로드 생성, blocks는 기본값 사용
    payload = DocRequest(
        repo_url=event.get('repo_url', ''),
        s3_path=event.get('s3_path', ''),
        include_test=event.get('include_test', False),
        korean=event.get('korean', False)
    )

    try:
        user_name, repo_name = parse_repo_url(event.get('repo_url', ''))

        readme_s3_key = f"{user_name}_{repo_name}_README.md"
        docs_s3_key = f"{user_name}_{repo_name}_DOCS.zip"
        # Lambda 함수 비동기 호출
        lambda_client.invoke(
            FunctionName="ai-generate",
            InvocationType='Event',  # 비동기 호출
            Payload=json.dumps({"body": json.dumps(payload.model_dump())})
        )
        response = {"readme_s3_key": readme_s3_key,
                    "docs_s3_key": docs_s3_key}
        # 비동기 호출이므로 즉시 성공 응답 반환
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }

    except Exception as e:
        print(f"Error invoking Lambda function: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error invoking Lambda function: {str(e)}")
        }
