"""
실행 위치 판별 유틸.

PyInstaller로 빌드된 exe에서는 __file__이 실행 파일 위치가 아니라
임시 압축 해제 폴더(_MEIPASS)를 가리키므로, .env/state.json처럼
exe와 나란히 있어야 하는 파일의 경로를 구할 때는 이 함수를 사용한다.
"""
import sys
from pathlib import Path


def base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent
