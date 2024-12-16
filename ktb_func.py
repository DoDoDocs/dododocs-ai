from ktb_settings import *
from urllib.parse import urlparse


"""**FUNCTIONS**"""


def parse_repo_url(repo_url: str):
    # URL 파싱
    parsed_url = urlparse(repo_url)

    # path에서 'user/repo.git' 추출 후 처리
    path_parts = parsed_url.path.strip('/').split('/')

    if len(path_parts) != 2:
        raise ValueError(f"잘못된 레포지토리 URL: {repo_url}")

    user_name, repo_name = path_parts
    repo_name = repo_name.replace('.git', '')  # '.git' 제거

    return repo_name, user_name
