import os
import zlib
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import override

from Crypto.Cipher import AES

from .sections import (Album, AlbumList, Artist, ArtistList, FileHeader, LibraryMaster,
                       Playlist, PlaylistList, Section, SectionHeader, Track,
                       TrackList)
from .util.byte_util import pack_int, unpack_int

KEY = b"BHUILuilfghuila3"
CIPHER = AES.new(KEY, AES.MODE_ECB)


# this default is suitable for Windows
DEFAULT_LIBRARY_FILE = Path(os.environ["USERPROFILE"]) / "Music" / "Apple Music" / "Apple Music Library.musiclibrary" / "Library.musicdb"


def load_library_bytes(file: Path | str = DEFAULT_LIBRARY_FILE) -> bytes:
    # copied from https://github.com/jsharkey13/musicdb-to-json get_library_bytes
    # changes:
    # - renames
    # - type annotations
    # - hardcoded the encryption key
    # - changed unpack_one to unpack_int

    with open(file, "rb") as f:
        file_bytes = f.read()

    assert file_bytes[:4] == b"hfma"

    header_size = unpack_int(file_bytes, 4)

    file_size = unpack_int(file_bytes, 8)
    assert len(file_bytes) == file_size

    compressed_size = file_size - header_size

    max_encrypted_size = unpack_int(file_bytes, 84)
    assert max_encrypted_size % 16 == 0  # AES128-ECB block size
    encrypted_size = compressed_size - (compressed_size % 16) if max_encrypted_size > file_size else max_encrypted_size

    # Some (but not all!) of the library data is encrypted. Apparently we decrypt the encrypted bytes:
    decrypted = b""
    if encrypted_size > 0:
        decrypted = CIPHER.decrypt(file_bytes[header_size:header_size + encrypted_size])

    # Then we just append on the rest of the file (which is not encrypted) and decompress:
    raw_bytes = zlib.decompress(decrypted + file_bytes[header_size + encrypted_size:])
    raw_bytes = file_bytes[:header_size] + raw_bytes

    return raw_bytes


def save_library_bytes(
    raw_bytes: bytes,
    file: Path | str = DEFAULT_LIBRARY_FILE,
    *,
    make_backup=True,
    raw=False,
):

    file = Path(file)
    if make_backup and file.exists():
        os.rename(file, file.with_stem(f"{file.stem} backup {datetime.now().isoformat(timespec="seconds").replace(":", ".")}"))

    # straightforward inverse of `load_library_bytes`
    if raw:
        with open(file, "wb") as f:
            f.write(raw_bytes)
            # note that I haven't bothered to update the file size in this case because that depends on the encryption/compression process
    else:
        assert raw_bytes[:4] == b"hfma"

        header_size = unpack_int(raw_bytes, 4)

        header = raw_bytes[:header_size]
        rest = raw_bytes[header_size:]

        compressed = zlib.compress(rest, 1)  # experimentally, this is the compression level that Apple Music
        compressed_size = len(compressed)

        max_encrypted_size = unpack_int(raw_bytes, 84)
        assert max_encrypted_size % 16 == 0  # AES128-ECB block size
        encrypted_size = compressed_size - (compressed_size % 16) if max_encrypted_size > compressed_size else max_encrypted_size

        encrypted = CIPHER.encrypt(compressed[:encrypted_size])
        rest_of_compressed = compressed[encrypted_size:]

        # encryption/compression changes the file size
        new_file_size_bytes = pack_int(len(header) + len(encrypted) + len(rest_of_compressed))

        with open(file, "wb") as f:
            f.write(header[:8])
            f.write(new_file_size_bytes)
            f.write(header[12:])
            f.write(encrypted)
            f.write(rest_of_compressed)


class Library(FileHeader):
    """ Represents the entire library as the (outer) hfma header with everything else as subsections.

    Subclass of `hfma` to get its class attributes, `__init__` already overrides the behavior to get subsections so no need to add/override the related attributes.

    This class does not maintain what would otherwise be its "total_size" (the length of the entire file) because that also depends on the encryption/compression process, so that's handled in `save_library_bytes`. """

    default_values = {
        "size": 160
    }

    @override
    def __init__(self, library: bytes | bytearray | Path | str = DEFAULT_LIBRARY_FILE):
        if isinstance(library, Path) or isinstance(library, str):
            library = load_library_bytes(library)

        data = BytesIO(library)
        super().__init__(data)

        # can't use superclass __init__ loop because the outer hfma header doesn't have anything corresponding to total_size or subsection_count, because the total file length is when the file is encrypted + compressed
        while data.tell() < len(library):
            self.subsections.append(
                SectionHeader(data)
            )
        assert data.tell() == len(library)

    def save(self, *args, **kwargs):
        save_library_bytes(b''.join(s.data for s in self), *args, **kwargs)

    def _grandchild_of_type[T: Section](self, type: type[T]) -> T:
        for h in self.subsections:
            if isinstance(h.child, type):
                return h.child
        raise KeyError

    @property
    def inner_file_header(self):
        return self._grandchild_of_type(FileHeader)

    @property
    def library_master(self):
        return self._grandchild_of_type(LibraryMaster)

    @property
    def albums(self):
        return self._grandchild_of_type(AlbumList)

    def album_by_id(self, id: int) -> Album:
        for a in self.albums.children:
            if a.get_int("id_album") == id:
                assert isinstance(a, Album)
                return a
        raise KeyError(id)

    @property
    def artists(self):
        return self._grandchild_of_type(ArtistList)

    def artist_by_id(self, id: int) -> Artist:
        for a in self.artists:
            if a.get_int("id_artist") == id:
                assert isinstance(a, Artist)
                return a
        raise KeyError(id)

    @property
    def tracks(self):
        return self._grandchild_of_type(TrackList)

    def track_by_id(self, id: int) -> Track:
        for t in self.tracks.children:
            if t.get_int("id_track") == id:
                assert isinstance(t, Track)
                return t
        raise KeyError(id)

    @property
    def playlists(self):
        return self._grandchild_of_type(PlaylistList)

    def playlist_by_id(self, id: int) -> Playlist:
        for p in self.playlists.children:
            if p.get_int("id_playlist") == id:
                assert isinstance(p, Playlist)
                return p
        raise KeyError(id)


if __name__ == "__main__":
    import sys
    file = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LIBRARY_FILE)
    save_library_bytes(
        load_library_bytes(file),
        "library.bin",
        make_backup=False,  # not saving to the same location
        raw=True
    )
