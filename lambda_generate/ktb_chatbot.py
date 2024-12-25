from ktb_prompts import *
from ktb_settings import *
from ktb_func import *

import os
from typing import List, Dict, Any
from pathlib import Path
import logging
import aiofiles
import asyncio
import concurrent.futures

"""**FUNCTION FOR CHAT**"""
# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


async def process_chunk(chunk, file_path, vector_store, file_metadata):
    """청크를 처리하고 벡터 스토어에 저장"""
    chunk_content = str(chunk).replace('\n', ' ').strip()
    if chunk_content:
        chunk_id = f"{file_path}_{chunk.start_index}"
        vector_store.upsert(
            documents=[chunk_content],
            metadatas=[{k: str(v) for k, v in file_metadata.items()}],
            ids=[chunk_id]
        )
        return 1
    return 0


async def process_file(file_path: Path, vector_store, file_metadata) -> int:
    """파일을 처리하고 청크 데이터를 벡터 스토어에 저장"""
    total_chunks = 0
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
            doc = await file.read()
            if doc.strip():
                chunks = embedding_chunker.chunk(doc)
                logger.info(f"file path : {
                            str(file_path)}, chunks size : {len(chunks)}")
                if chunks:
                    tasks = [
                        process_chunk(chunk, file_path,
                                      vector_store, file_metadata)
                        for chunk in chunks
                    ]
                    results = await asyncio.gather(*tasks)
                    total_chunks = sum(results)
    except UnicodeDecodeError as e:
        print(f"Unicode decode error in file {str(file_path)}: {str(e)}")
    except Exception as e:
        print(f"Error processing file {str(file_path)}: {str(e)}")
    return total_chunks


async def add_data_to_db(db_name: str, path: str, file_type: List[str]) -> int:
    """DB에 데이터를 추가"""
    try:
        vector_store = chroma_client.get_or_create_collection(
            name=db_name,
            embedding_function=embedding_func,
            metadata=DISTANCE
        )
        repo_path = Path(path)
        total_files_processed = 0
        processed_files = set()
        all_file_paths = []

        for root, _, files in os.walk(repo_path):
            for filename in files:
                if filename == '.DS_Store':
                    continue
                if any(filename.endswith(ft) or filename == ft for ft in file_type):
                    file_path = Path(root) / filename
                    if file_path.is_file():
                        all_file_paths.append(file_path)

        batch_size = 100  # 배치 크기 설정
        for i in range(0, len(all_file_paths), batch_size):
            try:
                batch_paths = all_file_paths[i:i + batch_size]
                tasks = []
                for file_path in batch_paths:
                    if file_path in processed_files:
                        print(f"Skipping already processed file: {
                              str(file_path)}")
                        continue
                    file_metadata = {
                        "filename": file_path.name,
                        "path": str(file_path),
                        "repository": str(db_name)
                    }
                    tasks.append(process_file(
                        file_path, vector_store, file_metadata))
                results = await asyncio.gather(*tasks)
                total_files_processed += sum(results)
                processed_files.update(batch_paths)
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                continue

        if total_files_processed == 0:
            print("No valid files were processed")
            print(f"{db_name}")
            print(f"{path}")
            return 0

        total_chunks = vector_store.count()
        print(f"Successfully processed {total_files_processed} files with total {
              total_chunks} chunks in {db_name}")
        return total_chunks
    except Exception as e:
        logger.error(f"Error adding data to DB: {str(e)}")
        raise
