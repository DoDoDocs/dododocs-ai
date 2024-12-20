from ktb_settings import *
from urllib.parse import urlparse


"""**FUNCTIONS**"""


def parse_repo_url(repo_url):
    """Extract user and repo name from the repo URL"""
    # Example implementation, adjust based on actual URL structure
    parts = repo_url.rstrip('/').split('/')
    user_name = parts[-3]
    repo_with_branch = parts[-2]+'_'+parts[-1]
    return user_name, repo_with_branch
