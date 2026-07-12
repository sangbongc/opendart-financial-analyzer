from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

CRTFC_KEY = os.getenv('crtfc_key')

BASE_URL = "https://opendart.fss.or.kr/api"

TIMEOUT = 10

# 프로젝트 최상위 폴더
BASE_DIR = Path(__file__).resolve().parent

# SQLite 데이터베이스 파일 경로
DB_PATH = BASE_DIR / "data" / "dart.db"