#Handle UTF-8 characters in the Python console, mainly for use with other languages
from __future__ import absolute_import

from core.compatibility import PYTHON_VERSION
from core.os import OPERATING_SYSTEM


if OPERATING_SYSTEM == 'Windows' and PYTHON_VERSION == 2:
    import core.utf8.win2
