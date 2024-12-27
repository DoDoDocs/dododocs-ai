import requests
from openai import OpenAI
import tiktoken
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import boto3
import os
import google.generativeai as genai
from token_chunker import TokenChunker
import json
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from typing import Mapping, Optional, cast, List
import logging
from chromadb import *
from openai import OpenAI
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import boto3
import os
from dotenv import load_dotenv
import google.generativeai as genai
import tiktoken
from token_chunker import TokenChunker
import requests


def load_config(config_path: str) -> dict:
    """설정 파일을 읽어와서 딕셔너리로 반환합니다."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except:
        print("no exists json config")
        return {}


EFS_CONFIG_PATH = os.getenv(
    'EFS_CONFIG_PATH', '/mnt/chroma_DB/setting/config.json')
config = load_config(EFS_CONFIG_PATH)

"""**PARAMETER SETTINGS**"""
MODEL = config.get('model_name', 'gemini-1.5-flash')
GPT_MODEL = config.get('gpt_model', 'gpt-4o-mini')
TEMPERATURE = config.get('temperature', 0.17)
SEED = config.get('seed', 213)
TOP_LOGPROBS = config.get('top_logprobs', 5)
EMBEDDING_MODEL = config.get('embedding_model_name', 'text-embedding-3-small')
DISTANCE_TYPE = config.get('distance_type', 'inner_product')
CHROMA_PATH = config.get('chroma_path', '/mnt/chroma_DB')
GPT_MAX_TOKENS = config.get('gpt_max_tokens', 120000)
MAX_RETRIES = config.get('max_retries', 1)  # 최대 재시도 횟수
RETRY_DELAY = config.get('retry_delay', 3)  # 재시도 간격 (초)
INCLUDE_TEST = config.get('include_test', False)
BUCKET_NAME = config.get('bucket_name', 'haon-dododocs')


if MODEL.startswith('gpt' or 'claude'):
    MAX_TOKENS_PER_BATCH = 1500000
elif MODEL.startswith('gemini'):
    MAX_TOKENS_PER_BATCH = 3500000

    # 임베딩 모델과 차원 설정
if EMBEDDING_MODEL == "text-embedding-3-small":
    EMBEDDING_DIM = 1536
elif EMBEDDING_MODEL == "text-embedding-3-large":
    EMBEDDING_DIM = 3072

if DISTANCE_TYPE == "cosine":
    DISTANCE = {"hnsw:space": "cosine"}
elif DISTANCE_TYPE == "inner_product":
    DISTANCE = {"hnsw:space": "ip"}
else:
    DISTANCE = {"hnsw:space": "l2"}

tokenizer = tiktoken.encoding_for_model(GPT_MODEL)
chunker = TokenChunker(
    tokenizer=tokenizer,
    chunk_size=GPT_MAX_TOKENS,  # maximum tokens per chunk
    chunk_overlap=128  # overlap between chunks
)
embedding_chunker = TokenChunker(
    tokenizer=tokenizer,
    chunk_size=8191,  # maximum tokens per chunk
    chunk_overlap=128  # overlap between chunks
)

FILE_EXTENSIONS = [
    '.py', '.pyw', '.pyc', '.pyo',  # Python
    '.java', '.class',     # Java
    '.c', '.h',                     # C
    '.cpp', '.hpp', '.cc', '.cxx',  # C++
    '.js', '.mjs',                  # JavaScript
    '.html', '.htm',                # HTML
    '.css',                         # CSS
    '.rb',                          # Ruby
    '.php',                         # PHP
    '.swift',                       # Swift
    '.go',                          # Go
    '.rs',                          # Rust
    '.kt', '.kts',                 # Kotlin
    '.R', '.r', '.Rmd',            # R
    '.scala',                       # Scala
    '.pl', '.pm',                  # Perl
    '.ts', '.tsx',                 # TypeScript
    '.sh', '.bash',                # Shell Script
    '.sql',                        # SQL
    'Dockerfile'
]

EXCLUDE_DIRS = ['.git', 'node_modules', 'venv', '__pycache__', 'dist', 'tests',
                'test', '.DS_Store', 'gradle-wrapper', '__MACOSX']

BUILD_FILE_NAMES = [
    'Makefile', 'CMakeLists.txt', 'setup.py', 'main.py', 'pyproject.toml',
    'config.js', 'go.mod', 'Cargo.toml', 'Gemfile', 'pom.xml', 'package.json',
    '.env', 'Dockerfile', 'requirements.txt', 'build',
    'setup.cfg', 'requirements-dev.txt', 'tox.ini', 'configure.ac', 'config.h.in',
    '.csproj', '.sln', 'tsconfig.json', 'webpack.config.js', 'gulpfile.js',
    'rollup.config.js', 'build.gradle', 'settings.gradle', 'Jenkinsfile',
    'Vagrantfile', 'Procfile', 'Brewfile', 'README.md', 'Dockerfile', 'docker-compose.yml', 'Makefile',
    'CMakeLists.txt', '.env', 'main.py', 'poetry.lock'
]

SRC_FILE_NAMES = ['.py', '.js', '.ts', '.java', '.cpp',
                  '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php']


def get_gemini_client(prompt: str):
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    return genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=prompt,
    )


OpenAI_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# ChromaDB 클라이언트 초기화
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

embedding_function = OpenAIEmbeddingFunction(
    api_key=os.getenv('OPENAI_API_KEY'), model_name=EMBEDDING_MODEL)


def self_embedding_function(texts: list[str], timeout: int = 80):
    try:
        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": EMBEDDING_MODEL,
            "input": texts
        }
        response = requests.post(url, headers=headers,
                                 json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return [item['embedding'] for item in data['data']]
    except requests.exceptions.Timeout:
        print("Request timed out.")
        return []
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return []


# S3 클라이언트 생성
s3 = boto3.client(
    's3'
)


class SelfEmbeddingFunction(EmbeddingFunction[List[str]]):
    def __init__(self, timeout: int = 80):
        self.timeout = timeout

    def __call__(self, texts: List[str]) -> Embeddings:
        try:
            url = "https://api.openai.com/v1/embeddings"
            headers = {
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": EMBEDDING_MODEL,
                "input": texts
            }
            response = requests.post(url, headers=headers,
                                     json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return [item['embedding'] for item in data['data']]
        except requests.exceptions.Timeout:
            print("Request timed out.")
            return []
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            return []


embedding_func = SelfEmbeddingFunction(timeout=60)
