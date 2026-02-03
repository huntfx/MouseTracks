import shutil
from itertools import count
from urllib.request import urlopen
from urllib.error import URLError
from pathlib import Path


def download_file(url: str, path: str | Path, timeout: int = 10) -> bool:
    """Download a file from a URL."""
    print(f'Downloading {url} to {path}...')
    try:
        with urlopen(url, timeout=timeout) as response, open(path, 'wb') as f:
            shutil.copyfileobj(response, f)
    except URLError as e:
        print(f'Error downloading {url}: {e}')
        return False
    return True


def safe_download_file(url: str, path: str | Path, timeout: int = 10) -> bool:
    """Safely download a file, ensuring it is only renamed."""
    path = Path(path)
    if path.exists():
        return False

    # Find the next available free filename
    for i in count():
        if i:
            temp = path.with_suffix(f'.tmp{i}')
        else:
            temp = path.with_suffix('.tmp')

        if temp.exists():
            try:
                temp.unlink()
            except OSError as e:
                print(f'Failed to clean up {temp.name}: {e}')
                continue
        break

    # Do the download to a temp location
    result = download_file(url, temp, timeout)

    # Rename the file to the correct name
    if result:
        try:
            if path.exists():
                path.unlink()
            temp.rename(path)
        except OSError as e:
            print(f'Error renaming {temp.name} to {path.name}: {e}')
            result = False

    # Clean up leftover temp file if it exists
    if temp.exists():
        try:
            temp.unlink()
        except OSError as e:
            print(f'Error cleaning up {temp.name}: {e}')

    return result
