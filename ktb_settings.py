from openai import OpenAI
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import os
from dotenv import load_dotenv

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

# 환경 변수로 실행 환경 확인
IS_DOCKER = os.getenv('IS_DOCKER', 'false').lower() == 'true'


CHROMA_PATH = "/mnt/chroma_DB"


# ChromaDB 클라이언트 초기화
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)


def get_openai_client():
    return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def get_embedding_function():
    return OpenAIEmbeddingFunction(
        api_key=os.getenv('OPENAI_API_KEY'), model_name=EMBEDDING_MODEL)
