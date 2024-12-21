from openai import OpenAI
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import os
import json


def load_config(config_path: str) -> dict:
    """설정 파일을 읽어와서 딕셔너리로 반환합니다."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except:
        print(f"Error: Config file not found at {config_path}")
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
CHROMA_PATH = config.get('chroma_path', '/mnt/chroma_DB/db')

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
# ChromaDB 클라이언트 초기화
print(CHROMA_PATH)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)


def get_openai_client():
    return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def get_embedding_function():
    return OpenAIEmbeddingFunction(
        api_key=os.getenv('OPENAI_API_KEY'), model_name=EMBEDDING_MODEL)
