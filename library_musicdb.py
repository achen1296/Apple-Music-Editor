import zlib
from pathlib import Path

from Crypto.Cipher import AES

from byte_util import expect, unpack_int

KEY = b"BHUILuilfghuila3"
CIPHER = AES.new(KEY, AES.MODE_ECB)


def library_header_sizes(library: bytes, check_file_size=True):
    """ `library` may be in either the file format or the raw format because the header is not modified as part of the transformation either way. """

    expect(library[:4], b"hfma", "musicdb file should start with hfma chunk!")

    header_size = unpack_int(library, 4)

    file_size = unpack_int(library, 8)
    if check_file_size:
        expect(len(library), file_size, "file size metadata mismatch!")

    data_size = file_size - header_size

    encrypted_size = unpack_int(library, 84)
    encrypted_size = data_size - (data_size % 16) if encrypted_size > file_size else encrypted_size

    return header_size, encrypted_size


def load_library(file: Path | str) -> bytes:
    # copied from https://github.com/jsharkey13/musicdb-to-json
    # changes:
    # - renames
    # - type annotations
    # - hardcoded the encryption key
    # - factored out library_header_sizes to also use in save_library (which has to not check the file size due to compression being part of the transformation)
    # - changed unpack_one to unpack_int

    with open(file, "rb") as f:
        file_bytes = f.read()

    header_size, encrypted_size = library_header_sizes(file_bytes)

    # Some (but not all!) of the library data is encrypted. Apparently we decrypt the encrypted bytes:
    decrypted = b""
    if encrypted_size > 0:
        decrypted = CIPHER.decrypt(file_bytes[header_size:header_size + encrypted_size])
    # Then we just append on the rest of the file (which is not encrypted) and decompress:
    raw_bytes = zlib.decompress(decrypted + file_bytes[header_size + encrypted_size:])
    raw_bytes = file_bytes[:header_size] + raw_bytes
    return raw_bytes


def save_library(file: Path | str, library: bytes,):
    # straightforward inverse of `load_library`

    header_size, encrypted_size = library_header_sizes(library, check_file_size=False)

    header = library[:header_size]
    rest = library[header_size:]

    compressed = zlib.compress(rest, 1)  # experimentally, this is the compression level that Apple Music uses

    encrypted = CIPHER.encrypt(compressed[:encrypted_size])
    rest_of_compressed = compressed[encrypted_size:]

    with open(file, "wb") as f:
        f.write(header + encrypted + rest_of_compressed)
