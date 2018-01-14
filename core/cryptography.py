"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Modified from paste.ubuntu.com/11024555 to support all input types

from __future__ import absolute_import

import hashlib
import struct

from core.compatibility import pickle
from core.config import CONFIG

#Attempt to import AES or create empty encryption class for the code to pass through
try:
    from Crypto.Cipher import AES
except ImportError:
    CONFIG['API']['_ServerEncryption'].lock = False
    CONFIG['API']['_ServerEncryption'] = False
    CONFIG['API']['_ServerEncryption'].lock = True
    class AES:
        MODE_ECB = 0
        class new(object):
            def __init__(self, *args): pass
            def encrypt(self, s): return s
            decrypt = encrypt
    
    
class DecryptionError(Exception):
    pass


def _pad16(s):
    s = pickle.dumps(s)
    t = struct.pack('>I', len(s)) + s
    return t + '\x00' * ((16 - len(t) % 16) % 16)


def _unpad16(s):
    n = struct.unpack('>I', s[:4])[0]
    try:
        return pickle.loads(s[4:n + 4])
    except pickle.UnpicklingError:
        raise DecryptionError('failed to decrypt message')


class Crypt(object):
    def __init__(self, password):
        pw_hash = hashlib.sha256(str(password)).digest()
        self.cipher = AES.new(pw_hash, AES.MODE_ECB)

    def encrypt(self, s):
        s = _pad16(s)
        return self.cipher.encrypt(s)

    def decrypt(self, s):
        t = self.cipher.decrypt(s)
        return _unpad16(t)
