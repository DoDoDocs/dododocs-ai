from typing import List
import os
import logging

logger = logging.getLogger(__name__)


class FileUtils:
    """파일 처리 관련 유틸리티"""
    @staticmethod
    def find_files(directory: str, extensions: tuple) -> List[str]:
        """지정된 확장자를 가진 파일들을 찾음"""
        files = []
        for root, _, filenames in os.walk(directory):
            # if any(excl in root for excl in EXCLUDE_DIRS):
            #    continue
            files.extend(
                os.path.join(root, f)
                for f in filenames
                if f.endswith(extensions)
            )
        return files