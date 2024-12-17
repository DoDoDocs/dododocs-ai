from openai import OpenAI
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import boto3
import os
from dotenv import load_dotenv
import google.generativeai as genai
from autotiktokenizer import AutoTikTokenizer
from token_chunker import TokenChunker
# .env 파일 로드
load_dotenv()

"""**PARAMETER SETTINGS**"""
# 모델 설정
MODEL = 'gemini-1.5-flash'
GPT_MODEL = 'gpt-4o-mini'
TEMPERATURE = 0.17
SEED = 213
TOP_LOGPROBS = 5  # logprob token 개수

if MODEL.startswith('gpt' or 'claude'):
    MAX_TOKENS_PER_BATCH = 1500000
    MAX_TOKEN_LENGTH = 120000
elif MODEL.startswith('gemini'):
    MAX_TOKENS_PER_BATCH = 3500000
    MAX_TOKEN_LENGTH = 1000000

tokenizer = AutoTikTokenizer.from_pretrained("gpt2")
chunker = TokenChunker(
    tokenizer=tokenizer,
    chunk_size=MAX_TOKEN_LENGTH,  # maximum tokens per chunk
    chunk_overlap=128  # overlap between chunks
)
embedding_chunker = TokenChunker(
    tokenizer=tokenizer,
    chunk_size=8191,  # maximum tokens per chunk
    chunk_overlap=2000  # overlap between chunks
)
embedding_model_name = os.getenv(
    'EMBEDDING_MODEL_NAME', 'text-embedding-3-small')
# 임베딩 모델과 차원 설정
if embedding_model_name == "text-embedding-3-small":
    EMBEDDING_MODEL = "text-embedding-3-small"
    EMBEDDING_DIM = 1536
elif embedding_model_name == "text-embedding-3-large":
    EMBEDDING_MODEL = "text-embedding-3-large"
    EMBEDDING_DIM = 3072

DISTANCE_TYPE = "inner_product"

if DISTANCE_TYPE == "cosine":
    DISTANCE = {"hnsw:space": "cosine"}
elif DISTANCE_TYPE == "inner_product":
    DISTANCE = {"hnsw:space": "ip"}
else:
    DISTANCE = {"hnsw:space": "l2"}

GPT_MAX_TOKENS = 120000

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
                'test', 'examples', 'example', '.DS_Store', 'gradle-wrapper', '__MACOSX']

BUILD_FILE_NAMES = [
    'Makefile', 'CMakeLists.txt', 'setup.py', 'main.py', 'pyproject.toml',
    'config.js', 'go.mod', 'Cargo.toml', 'Gemfile', 'pom.xml', 'package.json',
    '.env', 'Dockerfile', 'requirements.txt', 'build',
    'setup.cfg', 'requirements-dev.txt', 'tox.ini', 'configure.ac', 'config.h.in',
    '.csproj', '.sln', 'tsconfig.json', 'webpack.config.js', 'gulpfile.js',
    'rollup.config.js', 'build.gradle', 'settings.gradle', 'Jenkinsfile',
    'Vagrantfile', 'Procfile', 'Brewfile', '.md', 'Dockerfile', 'docker-compose.yml', 'Makefile',
    'CMakeLists.txt', '.env', 'main.py', 'poetry.lock'
]

SRC_FILE_NAMES = ['.py', '.js', '.ts', '.java', '.cpp',
                  '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php']

MAX_RETRIES = 2  # 최대 재시도 횟수
RETRY_DELAY = 3  # 재시도 간격 (초)
INCLUDE_TEST = False


def get_openai_client():
    return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def get_gemini_client(prompt: str):
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    return genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=prompt,
    )


client_gemini = OpenAI(
    api_key=os.getenv('GEMINI_API_KEY'),
    base_url="https://generativelanguage.googleapis.com/v1beta/"
)

CHROMA_PATH = "/mnt/chroma_DB"

# ChromaDB 클라이언트 초기화
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
embedding_function = OpenAIEmbeddingFunction(
    api_key=os.getenv('OPENAI_API_KEY'), model_name=EMBEDDING_MODEL)

# S3 클라이언트 생성
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
)

BUCKET_NAME = 'haon-dododocs'
