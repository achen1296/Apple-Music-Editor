import os
import zlib
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Iterable, Iterator, override

from Crypto.Cipher import AES

from byte_util import pack_int, pack_int_into, unpack_int

KEY = b"BHUILuilfghuila3"
CIPHER = AES.new(KEY, AES.MODE_ECB)


# this default is suitable for Windows
DEFAULT_LIBRARY_FILE = Path(os.environ["USERPROFILE"]) / "Music" / "Apple Music" / "Apple Music Library.musiclibrary" / "Library.musicdb"


def library_header_sizes(library: bytes, check_file_size=True):
    """ `library` may be in either the file format or the raw format because the header is not modified as part of the transformation either way. """

    assert library[:4] == b"hfma"

    header_size = unpack_int(library, 4)

    file_size = unpack_int(library, 8)
    if check_file_size:
        assert len(library) == file_size

    data_size = file_size - header_size

    encrypted_size = unpack_int(library, 84)
    encrypted_size = data_size - (data_size % 16) if encrypted_size > file_size else encrypted_size

    return header_size, encrypted_size


def load_library_bytes(file: Path | str = DEFAULT_LIBRARY_FILE) -> bytes:
    # copied from https://github.com/jsharkey13/musicdb-to-json get_library_bytes
    # changes:
    # - renames
    # - type annotations
    # - hardcoded the encryption key
    # - factored out library_header_sizes to also use in save (which has to not check the file size due to compression being part of the transformation)
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


def save_library_bytes(
    library: bytes,
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
            f.write(library)
            # note that I haven't bothered to update the file size in this case because that depends on the encryption/compression process
    else:
        header_size, encrypted_size = library_header_sizes(library, check_file_size=False)

        header = library[:header_size]
        rest = library[header_size:]

        compressed = zlib.compress(rest, 1)  # experimentally, this is the compression level that Apple Music uses

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


class Section:
    expected_signature: bytes = b""
    offsets: dict[str, int] = {
        "signature": 0,
        "size": 4,
        # -1 indicates that this kind of section doesn't have this, however these are common enough to include logic for them in the base class
        "total_size": -1,
        "subsection_count": -1,
        "date_modified": -1,
    }

    @property
    def signature(self):
        if not self._signature:
            # should never edit the signature
            self._signature = self._data[self.offsets["signature"]:self.offsets["signature"] + 4]
        return self._signature

    @property
    def size(self):
        if self._changed_size:
            pack_int_into(self._data, self.offsets["size"], len(self._data))
            # do not change back to self._changed_size = False because supersections might not have seen tha the size changed yet!
            # better to update the size multiple times redundantly than not to set it at all
        return len(self._data)

    @property
    def size_from_data(self):
        """ Use this one when loading! `size` will not be correct until this section is fully loaded! """
        return unpack_int(self._data, self.offsets["size"])

    @property
    def total_size(self):
        """ Size of this section and all subsections, referred to as "associated sections length" on vollink """
        if self.offsets["total_size"] >= 0 and any(s._changed_size for s in self):
            total_size = sum(s.size for s in self)
            pack_int_into(self._data, self.offsets["total_size"], total_size)
            return total_size
        else:
            return sum(s.size for s in self)

    @property
    def total_size_from_data(self):
        """ Use this one when loading! `total_size` will not be correct until this section and all subsections are loaded! """
        if self.offsets["total_size"] < 0:
            raise ValueError(f"{self.expected_signature} section doesn't have a stored total size")
        return unpack_int(self._data, self.offsets["total_size"])

    @property
    def subsection_count(self):
        """ Referred to as "how many sections follow" on vollink """
        if self.offsets["subsection_count"] >= 0 and self._subsection_count_changed:
            pack_int_into(self._data, self.offsets["subsection_count"], len(self.subsections))
            self._subsection_count_changed = False
        return len(self.subsections)

    def __init__(self, data: BytesIO):
        self._signature = None

        self._edited = False
        self._changed_size = False
        self._subsection_count_changed = False

        self._data = bytearray(data.read(self.offsets["size"] + 4))
        self._data += data.read(self.size_from_data - (self.offsets["size"] + 4))
        assert self.size == self.size_from_data  # make sure read() did not stop short

        assert self.expected_signature == self.signature, (self.expected_signature, self.signature)

        self.subsections: list["Section"] = []
        # subclass should take care of loading subsections, advancing the BytesIO accordingly

    def _edit(self):
        self._edited = True

    def _edit_change_size(self):
        self._edited = True
        self._changed_size = True

    def _edit_change_subsection_count(self):
        self._edited = True
        self._subsection_count_changed = True

    @property
    def data(self):
        # this makes sure everything is updated when we go to write

        if self.offsets["date_modified"] >= 0 and any(s._edited for s in self):
            # +2082844800 to convert Unix epoch (Jan 1 1970) to Mac epoch (Jan 1 1904)
            pack_int_into(self._data, self.offsets["date_modified"], int(datetime.now(tz=timezone.utc).timestamp()) + 2082844800)
            # do not change back to self._edited = False because supersections might not have seen yet

        # run the logic to update these in their property methods
        self.size
        self.total_size
        self.subsection_count

        return self._data

    def __iter__(self) -> Iterator["Section"]:
        """ Yield this section and all subsections (and subsubsections, etc.) in the order they would appear in the file """
        yield self
        for s in self.subsections:
            yield from s

    def __str__(self):
        return f"{self.__class__.__name__} [{", ".join(str(s) for s in self.subsections)}]"

    def __repr__(self):
        return self.__str__()

    def edit_int(self, offset: int, value: int):
        self._edit()
        pack_int_into(self._data, offset, value)


class boma(Section):
    expected_signature = b"boma"
    offsets = {
        **Section.offsets,
        "size": 8,  # only this section type has the size in a different place
    }


class hsma(Section):
    expected_signature = b"hsma"
    offsets = {
        **Section.offsets,
        "total_size": 8,
    }

    @override
    def __init__(self, data: BytesIO):
        super().__init__(data)
        data.read(self.total_size_from_data - self.size)  # todo actually read subsections


class Library(Section):
    # subclass of section due to representing the entire library as the hfma header with everything else as subsections
    expected_signature = b"hfma"
    # the entire library does not bother maintain its "total_size" (the length of the entire file) because that also depends on the encryption/compression process, so that's handled in `save_library_bytes`
    # however, I do make sure the modified date is set
    offsets = {
        **Section.offsets,
        "date_modified": 100
    }

    @override
    def __init__(self, library: bytes | bytearray | Path | str = DEFAULT_LIBRARY_FILE):
        if not (isinstance(library, bytes) or isinstance(library, bytearray)):
            library = load_library_bytes(library)

        bio = BytesIO(library)
        super().__init__(bio)

        while bio.tell() < len(library):
            self.subsections.append(
                hsma(bio)
            )

    def save(self, *args, **kwargs):
        save_library_bytes(b''.join(s.data for s in self), *args, **kwargs)


if __name__ == "__main__":
    print(Library())
