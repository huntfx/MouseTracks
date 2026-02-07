"""Implement custom signing to protect the executable delivery.

This is just an extra step to ensure the launcher only runs known executables.
A key is not required for building locally, but downloads will not be verified.
"""

import os
from pathlib import Path

from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError

from .constants import REPO_DIR, IS_BUILT_EXE, UNTRUSTED_EXT


MARKER = b'MT-SIG-V1'

KEY_PATH = REPO_DIR / 'keys'

PUBLIC_KEY_PATH = KEY_PATH / 'public.key'

PRIVATE_KEY_PATH = KEY_PATH / 'private.key'

PYTHON_KEY_PATH = Path('.').parent / '_sign.py'

PUBLIC_KEY_SIZE = 32

SIGNATURE_SIZE = 64


def generate_keys() -> None:
    """Generate a private and public key for building.

    Warning: Generating a new key will break all previous builds.
    Because of this, overwriting from code is not allowed.
    """
    assert not IS_BUILT_EXE

    print(f'Generating build keys...')
    if PRIVATE_KEY_PATH.exists():
        print('Existing private key found in folder, skipping')
        return

    private_key = SigningKey.generate()
    public_key = private_key.verify_key
    KEY_PATH.mkdir(exist_ok=True)
    PRIVATE_KEY_PATH.write_bytes(private_key.encode(encoder=HexEncoder))
    print(f'Saved private key to {PRIVATE_KEY_PATH}')
    PUBLIC_KEY_PATH.write_bytes(public_key.encode(encoder=HexEncoder))
    print(f'Saved public key to {PUBLIC_KEY_PATH}')


def write_public_key_to_py() -> Path | None:
    """Write the public key out to a file.
    This is slightly more secure than bundling `public.key` itself.
    """
    public_key = get_build_public_key()

    if public_key is None:
        print('No public key found, proceeding without signing')
        if PYTHON_KEY_PATH.exists():
            PYTHON_KEY_PATH.unlink()
        return None

    print('Public key found, executable will be signed')
    PYTHON_KEY_PATH.write_bytes(f'PUBLIC_KEY=b{public_key.decode("utf-8")!r}'.encode('utf-8'))
    return PYTHON_KEY_PATH


def get_build_public_key() -> bytes | None:
    """Get the public key used when building."""
    assert not IS_BUILT_EXE

    if PUBLIC_KEY_PATH.exists():
        return PUBLIC_KEY_PATH.read_bytes()
    return None


def get_build_private_key() -> bytes | None:
    """Get the public key used when building."""
    assert not IS_BUILT_EXE

    if PRIVATE_KEY_PATH.exists():
        return PRIVATE_KEY_PATH.read_bytes()
    return None


def get_runtime_public_key() -> bytes | None:
    """Get the public key when running as a script."""
    try:
        from . import _sign
    except ImportError:
        return None
    return _sign.PUBLIC_KEY


def sign_executable(exe_path: Path | str) -> bool:
    """Sign an executable with a public key."""
    exe_path = Path(exe_path)
    data = exe_path.read_bytes()
    private_key = get_build_private_key()

    if private_key is None:
        print('Failed to sign executable: no private key available')
        return False

    # Sign the data
    signing_key = SigningKey(private_key, encoder=HexEncoder)
    signed = signing_key.sign(data)
    signature = signed.signature

    # Add signature to the end of the executable
    with open(exe_path, 'ab') as f:
        f.write(MARKER)
        f.write(signature)

    print(f'Signed executable: {exe_path}')
    return True


def verify_signature(file_path: Path | str, write_untrusted: bool = True) -> bool:
    """Verify the signature on an executable."""
    file_path = Path(file_path)
    print(f'Checking signature of {file_path}...')

    # No signature supplied during build process
    public_key = get_runtime_public_key()
    if public_key is None:
        print(f'No public key set, signature verification disabled')
        return True

    # Read the last 10KB of the file
    with file_path.open('rb') as f:
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        read_size = min(file_size, 10240)
        f.seek(-read_size, os.SEEK_END)
        chunk = f.read(read_size)

        # Find the marker in the chunk
        marker_pos = chunk.rfind(MARKER)
        if marker_pos == -1:
            print(f'No signature found')
            if write_untrusted:
                _write_untrusted(file_path)
            return False

        # Extract signature and the data that was signed
        sig_start = marker_pos + len(MARKER)
        signature = chunk[sig_start : sig_start + SIGNATURE_SIZE]

        # Grab all the data before the signature
        marker_pos = file_size - read_size + marker_pos
        f.seek(0)
        signed_data = f.read(marker_pos)

    # Run the verification
    verify_key = VerifyKey(public_key, encoder=HexEncoder)
    try:
        verify_key.verify(signed_data, signature)
    except BadSignatureError as e:
        print(f'Failed verification: {e}')
        if write_untrusted:
            _write_untrusted(file_path)
        return False

    print(f'Signature verified')
    return True


def _write_untrusted(file_path: Path | str) -> None:
    """Append the public key to an "unstrusted" file.
    This is likely caused by a custom build attempting to run official
    releases, since they will be signed with a different key.
    """
    public_key = get_runtime_public_key()
    if public_key is None:
        return None

    # Only update if the public key is not already in the file
    if not failed_signature_verification(file_path):
        try:
            with Path(file_path).with_suffix(UNTRUSTED_EXT).open('ab') as f:
                f.write(public_key)
        except OSError as e:
            print(f'Failed to append data for failed signature check: {e}')


def failed_signature_verification(file_path: Path | str) -> bool:
    """Determine if an executable has already failed signature verification."""
    public_key = get_runtime_public_key()
    if public_key is None:
        return False

    untrusted_path = Path(file_path).with_suffix(UNTRUSTED_EXT)
    try:
        contents = untrusted_path.read_bytes()
    except FileNotFoundError:
        return False
    public_keys = (contents[i * PUBLIC_KEY_SIZE:(i + 1) * PUBLIC_KEY_SIZE]
                   for i in range(len(contents) // PUBLIC_KEY_SIZE))
    return public_key in public_keys
