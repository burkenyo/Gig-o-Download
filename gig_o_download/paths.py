from argparse import ArgumentTypeError
from io import TextIOWrapper
from pathlib import Path
from tempfile import NamedTemporaryFile
import os
import platformdirs

_APP_NAME = 'Gig-o-Download'
CACHE_PATH = platformdirs.user_cache_path(_APP_NAME, ensure_exists=True)
DEFAULT_DATA_PATH = Path(platformdirs.user_documents_path(), _APP_NAME)

def open_utf8(file: Path, mode: str, newline: str | None = None) -> TextIOWrapper:
    return file.open(mode, encoding='utf-8', newline=newline)

def read_utf8(file: Path) -> str:
    return file.read_text('utf-8')

def write_utf8(file: Path, contents: str):
    file.write_text(contents, 'utf-8')

def ensure_dir(base: Path, dir_name: str):
    dir = Path(base, dir_name)
    dir.mkdir(parents=True, exist_ok=True)
    return dir

def temporary_utf8_file(mode: str, suffix: str | None = None, delete_on_close: bool = True) -> NamedTemporaryFile:
    return NamedTemporaryFile(mode, encoding='utf-8', suffix=suffix, delete_on_close=delete_on_close)

def get_out_dir_from_arg(data_dir_name: str) -> Path:
    if not data_dir_name:
        return DEFAULT_DATA_PATH

    data_dir = Path(os.path.abspath(Path(data_dir_name).expanduser()))
    test_dir = data_dir

    while not test_dir.exists():
        test_dir = test_dir.parent

    if not test_dir.is_dir():
        raise ArgumentTypeError(f'{data_dir} is not a directory!')

    if not os.access(test_dir, os.W_OK):
        raise ArgumentTypeError(f'{data_dir} is not writeable!')

    return data_dir
