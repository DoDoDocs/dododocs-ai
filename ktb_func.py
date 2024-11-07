from ktb_settings import *
from ktb_func import *

import re
import os
from typing import List, Dict, Optional, Tuple, Any, Generator
from pathlib import Path
import git
from urllib.parse import urlparse
import zipfile

"""**FUNCTIONS**"""
def clone_git_repo(repo_url: str, clone_dir: str) -> bool:
    """Git 저장소를 클론하거나 갱신합니다."""
    try:
        if os.path.exists(clone_dir):
            repo = git.Repo(clone_dir)
            repo.remotes.origin.pull()
        else:
            git.Repo.clone_from(repo_url, clone_dir, recursive=True)
        return True
    except Exception as e:
        print(f"Git 작업 중 오류 발생: {str(e)}")
        return False

def extract_imported_classes(content):
    # Regex to find import statements
    import_pattern = r'import\s+([\w\.]+);'
    matches = re.findall(import_pattern, content)
    return matches

def read_file_content(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def file_list(path):
    # List to store the paths of Java files
    java_files = []
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith('.java'):
                java_files.append(os.path.join(root, file))

    print(f"Total Java files found: {len(java_files)}")
    return java_files

def check_service_annotation(java_files):
    service_files = []
    # 전체 내용에서 어노테이션을 찾는 정규 표현식
    pattern = re.compile(r'@(?:Service|Controller|RestController)\b')

    for file in java_files:
        if os.path.isfile(file):
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 전체 내용에서 어노테이션이 있는지 검사
                if pattern.search(content):
                    service_files.append(file)

    print("Service/Controller num :", len(service_files))
    return service_files

def get_path(file_path) :
    index = file_path.find("/main/java/") + len("/main/java/")
    result = file_path[:index]

    return result

def extract_filename(path):
    return Path(path).name

def get_code_extention(service_code_list):
    service_code_contents = []
    for service_code in service_code_list:
        total_code = ''
        path = get_path(service_code)
        with open(service_code, 'r') as file:
            content = file.read()

        imported_classes = extract_imported_classes(content)

        for class_name in imported_classes:
            class_path = class_name.replace('.', '/') + '.java'
            full_path = os.path.join(path, class_path)

            if os.path.exists(full_path):
                class_content = read_file_content(full_path)
                total_code = total_code + f"Content of {class_name} :\n{class_content}\n\n"
            else:
                pass
        total_code = total_code + f"Service code :\n{content}"
        service_code_contents.append(total_code)

    return service_code_contents

def parse_repo_url(repo_url: str):
    # URL 파싱
    parsed_url = urlparse(repo_url)
    
    # path에서 'user/repo.git' 추출 후 처리
    path_parts = parsed_url.path.strip('/').split('/')
    
    if len(path_parts) != 2:
        raise ValueError(f"잘못된 레포지토리 URL: {repo_url}")
    
    user, repo = path_parts
    repo = repo.replace('.git', '')  # '.git' 제거

    # clone_dir과 md_path 구성
    clone_dir = f"./{user}/{repo}"
    md_path = f"./{user}/{repo}/dododocs/"
    repo_name = f"{user}-{repo}"

    return clone_dir, md_path, repo_name


def download_zip_from_s3(bucket_name, object_key, download_path):
    """S3에서 ZIP 파일을 다운로드"""
    # 다운로드 경로의 디렉토리 부분 추출
    download_dir = os.path.dirname(download_path)
    # 디렉토리가 없으면 생성
    if download_dir and not os.path.exists(download_dir):
        os.makedirs(download_dir)
        print(f"디렉토리 생성됨: {download_dir}")
    
    s3.download_file(bucket_name, object_key, download_path)

def extract_zip(file_path, extract_to):
    """ZIP 파일의 압축 해제"""
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def create_zip(directory, zip_path):
    """디렉토리의 모든 파일을 ZIP으로 압축"""
    with zipfile.ZipFile(zip_path, 'w') as zip_ref:
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zip_ref.write(file_path, os.path.relpath(file_path, directory))

def upload_zip_to_s3(bucket_name, object_key, file_path):
    """ZIP 파일을 S3에 업로드"""
    s3.upload_file(file_path, bucket_name, object_key)

def get_presigned_url(bucket_name, object_key, expiration=3600):
    """프리사인드 URL 생성"""
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={'Bucket': bucket_name, 'Key': object_key},
        ExpiresIn=expiration  # URL의 유효 시간 (초 단위)
    )
    return url

# 예시 사용법
'''
# 단계별 실행
# 1. ZIP 파일 다운로드
md_url ="https://haon-dododocs.s3.ap-northeast-2.amazonaws.com/README.md"
download_zip_from_s3(bucket_name=bucket_name, object_key="README.md.zip", download_path="README.md.zip")
download_zip_from_s3(bucket_name=bucket_name, object_key="README.md.zip", download_path="./re/README.md.zip")
# 2. ZIP 파일 압축 해제
extract_zip("README.md.zip", "./")

# 3. 처리 후 ZIP 파일 생성
create_zip("./re", "./re.zip")

# 4. ZIP 파일 업로드
upload_zip_to_s3(bucket_name, "./README_test.md.zip", "./README_test.md.zip")

url = get_presigned_url(bucket_name, "README_test.md.zip")
print("Download URL:", url)
'''