"""Initialize the MouseTracks package environment."""

import os
import sys

from .runtime import REPO_DIR, IS_BUILT_EXE
from .version import VERSION as __version__
from .utils.system import force_physical_dpi_awareness

# Source DLL files globally
if IS_BUILT_EXE:
    sys.path.append(str(REPO_DIR / 'resources' / 'build'))

# Set SSL certs before any networking modules are imported
if IS_BUILT_EXE:
    cert_path = REPO_DIR / 'certifi' / 'cacert.pem'
    os.environ['SSL_CERT_FILE'] = str(cert_path)

# Force DPI Awareness before any GUI or user32 interactions occur
force_physical_dpi_awareness()
