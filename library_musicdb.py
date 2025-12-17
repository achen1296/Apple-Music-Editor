import os
import zlib
from datetime import datetime, timezone
from enum import Enum
from io import SEEK_CUR, BytesIO
from pathlib import Path
from typing import Callable, Iterable, Iterator, Type, override

from Crypto.Cipher import AES

from byte_util import pack_int, pack_int_into, show_control_chars, unpack_int

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


SECTION_CLASSES: dict[bytes, Type["Section"]] = {}


def register_section_class(cls: Type["Section"]):
    SECTION_CLASSES[bytes(cls.__name__, "ascii")] = cls


class Section:
    offsets: dict[str, int] = {
        "signature": 0,
        "size": 4,
        # -1 indicates that this kind of section doesn't have this, however these are common enough to include logic for them in the base class
        "total_size": -1,
        "subsection_count": -1,
        "date_modified": -1,
    }
    allowed_subsections: set[bytes] = set()
    check_signature = True  # only disabled for Library which has hfma signature

    def __init__(self, data: BytesIO, check_signature=True):
        self._signature = None

        self._edited = False
        self._changed_size = False
        self._updated_size_after_change = True
        self._subsection_count_changed = False

        start_offset = data.tell()

        # read this section
        self._data = bytearray(data.read(self.offsets["size"] + 4))
        self._data += data.read(self.size_from_data - (self.offsets["size"] + 4))
        assert self.size == self.size_from_data  # make sure read() did not stop short

        if self.check_signature and check_signature:  # can be turned off either at class level or by caller
            assert SECTION_CLASSES[bytes(self.signature)] is self.__class__, (SECTION_CLASSES[bytes(self.signature)], self.__class__)

        # read subsections -- only if there is either a total size or a subsection count in the data (sometimes both are present, doesn't matter which is used in that case for a valid file)
        self.subsections: list["Section"] = []

        def append_subsection():
            signature = data.read(4)
            data.seek(-4, SEEK_CUR)

            if signature in SECTION_CLASSES:
                if signature in self.allowed_subsections:
                    self.subsections.append(
                        SECTION_CLASSES[signature](data)
                    )
                else:
                    raise ValueError(f"unexpected subsection signature {signature} for subsection of {self.__class__.__name__}")
            else:
                print(f"warning: unknown signature {signature}, loading it with the `Section` base class")
                self.subsections.append(
                    Section(data, check_signature=False)  # use a generic section just to have something for limited forward compatibility with unknown future section types
                )

        if self.offsets["total_size"] > 0:
            total_size = self.total_size_from_data
            while data.tell() < start_offset + total_size:
                append_subsection()
            assert data.tell() == start_offset + total_size
        elif self.offsets["subsection_count"] > 0:
            for _ in range(0, self.subsection_count_from_data):
                append_subsection()

    @property
    def signature(self):
        if not self._signature:
            # should never edit the signature
            self._signature = self._data[self.offsets["signature"]:self.offsets["signature"] + 4]
        return self._signature

    @property
    def size(self):
        if not self._updated_size_after_change and self._changed_size:
            self.set_int("size", len(self._data))
            # do not change back to self._changed_size = False because supersections might not have seen tha the size changed yet!
            # better to update the size multiple times redundantly than not to set it at all
            self._updated_size_after_change = True
        return len(self._data)

    @property
    def size_from_data(self):
        """ Use this one when loading! `size` will not be correct until this section is fully loaded! """
        return self.get_int("size")

    @property
    def total_size(self):
        """ Size of this section and all subsections, referred to as "associated sections length" on vollink """
        if self.offsets["total_size"] >= 0 and any(s._changed_size for s in self):
            total_size = sum(s.size for s in self)
            self.set_int("total_size", total_size)
            return total_size
        else:
            return sum(s.size for s in self)

    @property
    def total_size_from_data(self):
        """ Use this one when loading! `total_size` will not be correct until this section and all subsections are loaded! """
        if self.offsets["total_size"] < 0:
            raise ValueError(f"{self.__class__.__name__} section doesn't have a stored total size")
        return self.get_int("total_size")

    @property
    def subsection_count(self):
        """ Referred to as "how many sections follow" on vollink """
        if self.offsets["subsection_count"] >= 0 and self._subsection_count_changed:
            self.set_int("subsection_count", len(self.subsections))
            self._subsection_count_changed = False
        return len(self.subsections)

    @property
    def subsection_count_from_data(self):
        """ Use this one when loading! `subsection_count` will not be correct until this section and all subsections are loaded! """
        if self.offsets["subsection_count"] < 0:
            raise ValueError(f"{self.__class__.__name__} section doesn't have a stored subsection count")
        return self.get_int("subsection_count")

    def _edit(self):
        self._edited = True

    def _edit_change_size(self):
        self._edited = True
        self._changed_size = True
        self._updated_size_after_change = False

    def _edit_change_subsection_count(self):
        self._edited = True
        self._subsection_count_changed = True

    @property
    def data(self):
        # this makes sure everything is updated when we go to write

        if self.offsets["date_modified"] >= 0 and any(s._edited for s in self):
            # +2082844800 to convert Unix epoch (Jan 1 1970) to Mac epoch (Jan 1 1904)
            self.set_int("date_modified", int(datetime.now(tz=timezone.utc).timestamp()) + 2082844800)
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
        if self.subsections:
            return f"{self.__class__.__name__} [{", ".join(str(s) for s in self.subsections)}]"
        else:
            return f"{self.__class__.__name__}"

    def __repr__(self):
        return self.__str__()

    def set_int(self, offset: int | str, value: int):
        self._edit()
        if isinstance(offset, str):
            offset = self.offsets[offset]
        pack_int_into(self._data, offset, value)

    def get_int(self, offset: int | str):
        if isinstance(offset, str):
            offset = self.offsets[offset]
        return unpack_int(self._data, offset)


class hsma(Section):
    offsets = {
        **Section.offsets,
        "total_size": 8,
    }
    allowed_subsections = {
        b"hfma",
        b"plma",
        b"lama",
        b"lAma",
        b"ltma",
        b"lPma",
        b"LPma",
    }


register_section_class(hsma)


class hfma(Section):  # inner hfma only, not outer hfma which is Library
    offsets = {
        **Section.offsets,
    }


register_section_class(hfma)


class plma(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    allowed_subsections = {b"boma"}


register_section_class(plma)


class lama(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    allowed_subsections = {b"iama"}


register_section_class(lama)


class iama(Section):
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
    }
    allowed_subsections = {b"boma"}


register_section_class(iama)


class lAma(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    allowed_subsections = {b"iAma"}


register_section_class(lAma)


class iAma(Section):
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
    }
    allowed_subsections = {b"boma"}


register_section_class(iAma)


class ltma(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    allowed_subsections = {b"itma"}


register_section_class(ltma)


class itma(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 12,
    }
    allowed_subsections = {b"boma"}


register_section_class(itma)


class lPma(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    allowed_subsections = {b"lpma"}


register_section_class(lPma)


class lpma(Section):
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
    }
    allowed_subsections = {b"boma"}


register_section_class(lpma)


class boma(Section):
    offsets = {
        **Section.offsets,
        "size": 8,  # only this section type has the size in a different place
        "boma_subtype": 12,
    }

    def get_string(self):
        """ See `set_string` """
        string_format = self.get_int(20)
        if string_format == 1:
            return self._data[36:].decode("utf_16_le")
        elif string_format == 2:
            return self._data[36:].decode("utf_8")
        else:
            return self._data[20:].decode("utf_8")


    def set_string(self, value: str):
        """ Checks offset 20 to see if it's 1 or 2 to determine the string format -- but if it's not either of these, defaults to writing UTF-8 at offset 20 instead! Other than that, this function does not know (this cannot be 100% reliably figured out from the data itself) if the data is supposed to be a string at all, so the caller should know that in advance (from the subtype number) or risk corruption. See readme/vollink.

        No offset argument because each boma can only contain one string at most (book types not supported -- see readme). """

        self._edit_change_size()

        string_format = self.get_int(20)
        if string_format == 1:
            self._data[36:] = value.encode("utf_16_le")
            # superclass will take care of the section length
            self.set_int(24, self.size - 36)
        elif string_format == 2:
            self._data[36:] = value.encode("utf_8")
            self.set_int(24, self.size - 36)
        else:
            self._data[20:] = value.encode("utf_8")


register_section_class(boma)


# see readme
class LPma(Section):
    offsets = {
        **Section.offsets,
    }


register_section_class(LPma)


class Library(Section):
    # subclass of Section -- representing the entire library as the (outer) hfma header with everything else as subsections
    # the entire library does not bother maintain its "total_size" (the length of the entire file) because that also depends on the encryption/compression process, so that's handled in `save_library_bytes`
    # however, I do make sure the modified date is set
    offsets = {
        **Section.offsets,
        "date_modified": 100
    }
    check_signature = False # hfma signature is registered for the inner one

    @override
    def __init__(self, library: bytes | bytearray | Path | str = DEFAULT_LIBRARY_FILE):
        if not (isinstance(library, bytes) or isinstance(library, bytearray)):
            library = load_library_bytes(library)

        data = BytesIO(library)
        super().__init__(data)

        # can't use superclass __init__ loop because the outer hfma header doesn't have anything corresponding to total_size or subsection_count, because the total file length is supposed to be AFTER encryption+compression
        while data.tell() < len(library):
            self.subsections.append(
                hsma(data)
            )

        assert data.tell() == len(library)

    def save(self, *args, **kwargs):
        save_library_bytes(b''.join(s.data for s in self), *args, **kwargs)


if __name__ == "__main__":
    library = Library()
    # print(library)
