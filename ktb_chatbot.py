from ktb_prompts import *
from ktb_settings import *
from ktb_func import *

from typing import List, Dict, Optional, Any, Generator, Union
import tiktoken


def db_search(query: str, db: Any, n_results: int = 3) -> Dict[str, Any]:
    """
    Search the vector database for similar documents.

    Args:
        query (str): Search query
        db: ChromaDB collection
        n_results (int): Number of results to return
        threshold (float): Similarity threshold

    Returns:
        Dict[str, Any]: Search results including documents and metadata
    """
    try:
        results = db.query(
            query_texts=query,
            n_results=n_results,
            include=["metadatas", "documents"]
        )
        filenames = [metadata['filename']
                     for metadata in results['metadatas'][0]]
        print(f"filenames: {filenames}")
        return results, filenames

    except Exception as e:
        raise


def _build_context(retrieved_docs: Dict[str, Any], filenames: List[str]) -> str:
    """Build context string from retrieved documents."""
    context = ""
    if retrieved_docs and filenames:
        for i in range(len(retrieved_docs['documents'][0])):
            if 'filename' in retrieved_docs['metadatas'][0][i]:
                context += f"\nFILENAME: {retrieved_docs['metadatas'][0][i]['filename']}\nFILE DOCUMENT : {
                    retrieved_docs['documents'][0][i]}\n"
    return context


def _create_prompt(query: str, source_context: str, generated_context: str, chat_history: Optional[List[dict]] = None) -> List[Dict[str, str]]:
    """Create a prompt for the LLM."""
    system_prompt = CHATBOT_PROMPT
    user_prompt = f"""
Retrieved Code Content:
{source_context}

Retrieved Document Content:
{generated_context}

User Query / Instruct: {query}
"""
    full_prompt = [{"role": "system", "content": system_prompt}]
    if chat_history:
        full_prompt.extend(chat_history)
    full_prompt.append({"role": "user", "content": user_prompt})
    return full_prompt


def generate_response(query: str, db_list: List[Any], chat_history: Optional[List[dict]] = None, augmented_query: Optional[str] = None, stream: bool = False) -> str:
    """Generate a response using LLM based on retrieved documents."""
    try:
        if augmented_query:
            retrieved_docs_source, filenames_source = db_search(
                augmented_query, db_list[0])
            retrieved_docs_generated, filenames_generated = db_search(
                augmented_query, db_list[1], n_results=2)
        else:
            retrieved_docs_source, filenames_source = db_search(
                query, db_list[0])
            retrieved_docs_generated, filenames_generated = db_search(
                query, db_list[1], n_results=2)

        source_context = _build_context(
            retrieved_docs_source, filenames_source)
        generated_context = _build_context(
            retrieved_docs_generated, filenames_generated)

        full_prompt = _create_prompt(
            query, source_context, generated_context, chat_history)

        client_gpt = get_openai_client()
        response = client_gpt.chat.completions.create(
            model=GPT_MODEL,
            messages=full_prompt,
            temperature=0.32,
            stream=False
        )

        return response.choices[0].message.content

    except Exception as e:
        raise


def stream_response(query: str, db_list: List[Any], chat_history: Optional[List[dict]] = None, augmented_query: Optional[str] = None) -> Generator:
    """Generate a streaming response."""
    try:
        if augmented_query:
            retrieved_docs_source, filenames_source = db_search(
                augmented_query, db_list[0])
            retrieved_docs_generated, filenames_generated = db_search(
                augmented_query, db_list[1], n_results=2)
        else:
            retrieved_docs_source, filenames_source = db_search(
                query, db_list[0])
            retrieved_docs_generated, filenames_generated = db_search(
                query, db_list[1], n_results=2)

        source_context = _build_context(
            retrieved_docs_source, filenames_source)
        generated_context = _build_context(
            retrieved_docs_generated, filenames_generated)

        full_prompt = _create_prompt(
            query, source_context, generated_context, chat_history)

        client_gpt = get_openai_client()
        response = client_gpt.chat.completions.create(
            model=GPT_MODEL,
            messages=full_prompt,
            temperature=0.52,
            stream=True
        )

        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

    except Exception as e:
        raise


def codebase_chat(query: str, repo_url: str, chat_history: List[dict] = None, stream: bool = False) -> Union[str, Generator]:
    """채팅 응답 생성"""
    try:
        user_name, repo_name = parse_repo_url(repo_url)
        collection_list = [
            collention.name for collention in chroma_client.list_collections()]
        if f"{repo_name}_source" in collection_list and f"{repo_name}_generated" in collection_list:
            vector_store_source = chroma_client.get_or_create_collection(
                name=f"{repo_name}_source",
                embedding_function=get_embedding_function()
            )
            vector_store_generated = chroma_client.get_or_create_collection(
                name=f"{repo_name}_generated",
                embedding_function=get_embedding_function()
            )
        else:
            raise Exception(
                f"Collection {repo_name}_source or {repo_name}_generated does not exist")
        db_list = [vector_store_source, vector_store_generated]
        if chat_history:
            total_content = ''.join([msg['content']
                                    for msg in chat_history]) + query
            total_tokens = len(tiktoken.encoding_for_model(
                GPT_MODEL).encode(total_content))
            last_message = chat_history[-1] if total_tokens > MAX_TOKEN_LENGTH else chat_history
        else:
            last_message = None

        augmented_query = query_augmentation(query, last_message)

        if stream:
            return stream_response(query, db_list, last_message, augmented_query)
        else:
            return generate_response(query, db_list, last_message, augmented_query, stream)

    except Exception as e:
        raise


def query_augmentation(query: str, chat_history: Optional[List[dict]] = None) -> str:
    """
    주어진 쿼리와 이전 응답을 분석하여 추가 검색이 필요한 정보를 식별하고 검색 쿼리를 생성합니다.

    Args:
        query (str): 사용자 입력 쿼리
        previous_query (str): 이전 쿼리 내용
        previous_response (str): 이전 응답 내용
    Returns:
        str: 증강된 검색 쿼리
    """
    prompt = AUGMENTATION_PROMPT

    if chat_history and len(chat_history) >= 2:
        previous_query = chat_history[-2]['content']
        previous_response = chat_history[-1]['content']
    else:
        previous_query = ""
        previous_response = ""

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"Previous Query: {
            previous_query}\nPrevious Response: {previous_response}\nQuery: {query}"}
    ]
    client_gpt = get_openai_client()
    augmented_query = client_gpt.chat.completions.create(
        model=GPT_MODEL,
        messages=messages,
        temperature=0.52,
        max_tokens=150,
    )

    return augmented_query.choices[0].message.content
