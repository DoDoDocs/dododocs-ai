from openai import OpenAI
from langchain_text_splitters import MarkdownHeaderTextSplitter
import anthropic
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import boto3
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수 가져오기
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY') 
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')


# 필수 환경 변수 확인
required_vars = [
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
]

for var in required_vars:
    if not os.getenv(var):
        raise ValueError(f"Required environment variable {var} is not set")
    

"""**PARAMETER SETTINGS**"""
#모델 설정
MODEL = 'gpt-4o-mini' #or gpt-4o
#MODEL = 'claude-3-5-sonnet-20241022'
TEMPERATURE = 0.1
SEED = 213
TOP_LOGPROBS = 5 #logprob token 개수
MAX_TOKEN_LENGTH = 120000

EMBEDDING_MODEL = "text-embedding-ada-002"
embedding_dim = 1536
DISTANCE = {"hnsw:space": "cosine"}

headers_to_split_on = [
    (
        "#",
        "Header 1",
    ),
    (
        "##",
        "Header 2",
    ),
    (
        "###",
        "Header 3",
    )
]
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
    '.md'                           # Markdown
]
exclude_dirs = ['.git', 'node_modules', 'venv', '__pycache__', 'dist', 'tests', 'test', 'examples', 'example', '.DS_Store', 'gradle-wrapper','__MACOSX']
build_file_names = [
        'Makefile', 'CMakeLists.txt', 'setup.py', 'main.py', 'pyproject.toml',
        'config.js', 'go.mod', 'Cargo.toml', 'Gemfile', 
        'pom.xml', 'package.json', '.env', 'Dockerfile', 'gradle', 'requirements.txt' ,'build'
    ]
src_file_names = ['.py', '.js', '.ts', '.java', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php']

client_gpt = OpenAI(api_key=OPENAI_API_KEY)
client_claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
chroma_client = chromadb.PersistentClient(
    path="/app/chroma_data"  # Docker 내부 경로
)
markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on,strip_headers=False)
embedding_function = OpenAIEmbeddingFunction(api_key=OPENAI_API_KEY, model_name=EMBEDDING_MODEL)

# S3 클라이언트 생성
s3 = boto3.client(
	's3',
	aws_access_key_id=AWS_ACCESS_KEY_ID,
	aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)
bucket_name = 'haon-dododocs'