from dotenv import load_dotenv
import os

load_dotenv()

CRTFC_KEY = os.getenv('crtfc_key')

BASE_URL = "https://opendart.fss.or.kr/api"

TIMEOUT = 10