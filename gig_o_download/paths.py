from io import TextIOWrapper
from pathlib import Path
from tempfile import NamedTemporaryFile
import platformdirs

def open_utf8(file: Path, mode: str, newline: str | None = None) -> TextIOWrapper:
    return file.open(mode, encoding='utf-8', newline=newline)

def read_utf8(file: Path) -> str:
    return file.read_text('utf-8')

def write_utf8(file: Path, contents: str):
    file.write_text(contents, 'utf-8')

def ensure_dir(base: Path, dir_name: str):
    dir = Path(base, dir_name)
    dir.mkdir(exist_ok=True)
    return dir

def temporary_utf8_file(mode: str, suffix: str | None = None, delete_on_close: bool = True) -> NamedTemporaryFile:
    return NamedTemporaryFile(mode, encoding='utf-8', suffix=suffix, delete_on_close=delete_on_close)

_APP_NAME = 'Gig-o-Download'
CACHE_PATH = platformdirs.user_cache_path(_APP_NAME, ensure_exists=True)
DATA_PATH = ensure_dir(platformdirs.user_documents_path(), _APP_NAME)
