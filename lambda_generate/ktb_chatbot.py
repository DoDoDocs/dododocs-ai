from ktb_prompts import *
from ktb_settings import *
from ktb_func import *

import os
from typing import List
from pathlib import Path
import logging
import tiktoken
import aiofiles

"""**FUNCTION FOR CHAT**"""
# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


async def add_data_to_db(db_name: str, path: str, file_type: List[str]) -> int:
    """DB에 데이터를 추가"""
    try:
        vector_store = chroma_client.get_or_create_collection(
            name=db_name,
            embedding_function=embedding_function,
            metadata=DISTANCE
        )
        repo_path = Path(path)
        total_files_processed = 0
        processed_files = set()

        async def process_file(file_path: Path, vector_store, file_metadata) -> int:
            """파일을 처리하고 벡터 스토어에 추가, 이미 처리된 파일은 건너뜁니다."""
            if file_path in processed_files:
                logger.info(f"Skipping already processed file: {file_path}")
                return 0

            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as file:
                    doc = await file.read()
                    if doc.strip():
                        if file_path.suffix == '.md':
                            chunks = embedding_chunker.chunk(doc)
                            if chunks:
                                chunk_contents = [
                                    chunk.text.replace('\n', ' ').strip()
                                    for chunk in chunks if chunk.text.strip()
                                ]
                                if chunk_contents:
                                    chunk_ids = [
                                        f"{file_path}_{i}"
                                        for i in range(len(chunk_contents))
                                    ]
                                    chunk_metadatas = [
                                        file_metadata for _ in range(len(chunk_contents))]
                                    vector_store.upsert(
                                        documents=chunk_contents,
                                        metadatas=chunk_metadatas,
                                        ids=chunk_ids
                                    )
                                    processed_files.add(file_path)
                                    return len(chunk_contents)
                        else:
                            if len(tiktoken.encoding_for_model(EMBEDDING_MODEL).encode(doc)) <= 8191:
                                vector_store.upsert(
                                    documents=[doc.replace('\n', ' ').strip()],
                                    metadatas=[file_metadata],
                                    ids=[f"{file_path}"]
                                )
                                processed_files.add(file_path)
                                return 1
                            else:
                                max_chunk_size = 8192
                                overlap_size = 100
                                chunks = [
                                    doc[i:i + max_chunk_size]
                                    for i in range(0, len(doc), max_chunk_size - overlap_size)
                                ]
                                chunk_ids = [
                                    f"{file_path}_{i}"
                                    for i in range(len(chunks))
                                ]
                                chunk_metadatas = [
                                    file_metadata for _ in range(len(chunks))]
                                vector_store.upsert(
                                    documents=chunks,
                                    metadatas=chunk_metadatas,
                                    ids=chunk_ids
                                )
                                processed_files.add(file_path)
                                print(f"Successfully processed file: {
                                      file_metadata['filename']} - Added {len(chunks)} chunks")
                                return len(chunks)

            except UnicodeDecodeError as e:
                logger.error(f"Unicode decode error in file {
                             file_path}: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
            return 0

        for root, _, files in os.walk(repo_path):
            for filename in files:
                if filename == '.DS_Store':
                    continue
                if any(filename.endswith(ft) or filename == ft for ft in file_type):
                    file_path = Path(root) / filename
                    if file_path.is_file():
                        file_metadata = {
                            "filename": filename,
                            "path": str(file_path),
                            "repository": db_name
                        }
                        chunks_added = await process_file(file_path, vector_store, file_metadata)
                        if chunks_added > 0:
                            total_files_processed += chunks_added

        if total_files_processed == 0:
            logger.error("No valid files were processed")
            return 0

        total_chunks = vector_store.count()
        print(f"Successfully processed {total_files_processed} files with total {
              total_chunks} chunks in {db_name}")
        return total_chunks
    except Exception as e:
        logger.error(f"Error adding data to DB: {str(e)}")
        raise
