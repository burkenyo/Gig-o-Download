from pathlib import Path
import platformdirs

APP_NAME = 'Gig-o-Download'
CACHE_PATH = platformdirs.user_cache_path(APP_NAME, ensure_exists=True)
AUTH_COOKIE_FILE = Path(CACHE_PATH, 'auth-cookie.txt')
DATA_PATH = Path(platformdirs.user_documents_path(), APP_NAME)
DATA_PATH.mkdir(exist_ok=True)
