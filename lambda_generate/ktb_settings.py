from openai import OpenAI
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import boto3
import os
import google.generativeai as genai
from autotiktokenizer import AutoTikTokenizer
from token_chunker import TokenChunker
import json


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
MAX_RETRIES = 1  # config.get('max_retries', 2)  # 최대 재시도 횟수
RETRY_DELAY = config.get('retry_delay', 3)  # 재시도 간격 (초)
INCLUDE_TEST = False  # config.get('include_test', False)
BUCKET_NAME = config.get('bucket_name', 'haon-dododocs')


if MODEL.startswith('gpt' or 'claude'):
    MAX_TOKENS_PER_BATCH = 1500000
    MAX_TOKEN_LENGTH = 120000
elif MODEL.startswith('gemini'):
    MAX_TOKENS_PER_BATCH = 3500000
    MAX_TOKEN_LENGTH = 1000000

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

os.environ['HF_HOME'] = '/tmp/huggingface'
tokenizer = AutoTikTokenizer.from_pretrained("gpt2")
chunker = TokenChunker(
    tokenizer=tokenizer,
    chunk_size=MAX_TOKEN_LENGTH,  # maximum tokens per chunk
    chunk_overlap=128  # overlap between chunks
)
embedding_chunker = TokenChunker(
    tokenizer=tokenizer,
    chunk_size=8191,  # maximum tokens per chunk
    chunk_overlap=200  # overlap between chunks
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


def get_openai_client():
    return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def get_gemini_client(prompt: str):
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    return genai.GenerativeModel(
        model_name=MODEL,
        system_instruction=prompt,
    )


OpenAI_client = get_openai_client()
# ChromaDB 클라이언트 초기화
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

embedding_function = OpenAIEmbeddingFunction(
    api_key=os.getenv('OPENAI_API_KEY'), model_name=EMBEDDING_MODEL)

# S3 클라이언트 생성
s3 = boto3.client(
    's3'
)


print(chroma_client.list_collections())
