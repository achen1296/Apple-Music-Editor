import os
import zlib
from datetime import datetime, timezone
from enum import Enum
from io import SEEK_CUR, BytesIO
from pathlib import Path
from re import M
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
    expected_subsections: set[bytes] = set()
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

        def append_subsection(error_on_unexpected: bool):
            signature = data.read(4)
            data.seek(-4, SEEK_CUR)

            if signature in SECTION_CLASSES:
                if signature in self.expected_subsections:
                    self.subsections.append(
                        SECTION_CLASSES[signature](data)
                    )
                else:
                    if error_on_unexpected:
                        raise ValueError(f"known signature {signature} but not expected as a subsection of {self.__class__.__name__} and using a subsection count, don't know how to proceed")
                    else:
                        print(f"warning: known signature {signature} but not expected as a subsection of {self.__class__.__name__}, but can proceed using total size")
            else:
                if error_on_unexpected:
                    raise ValueError(f"unknown signature {signature} and using a subsection count, don't know how to proceed")
                else:
                    print(f"warning: unknown signature {signature}, loading it with the `Section` base class, but can proceed using total size")
                self.subsections.append(
                    Section(data, check_signature=False)  # use a generic section just to have something for limited forward compatibility with unknown future section types
                )

        self.parent = self  # won't be reassigned if this is the top-level Section

        if self.offsets["total_size"] > 0:
            # total size is preferred if both are available because it has a better chance of being able to proceed for unknown sections
            total_size = self.total_size_from_data
            while data.tell() < start_offset + total_size:
                append_subsection(error_on_unexpected=False)
            assert data.tell() == start_offset + total_size
        elif self.offsets["subsection_count"] > 0:
            for _ in range(0, self.subsection_count_from_data):
                append_subsection(error_on_unexpected=True)

        for s in self.subsections:
            s.parent = self

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
        """ Yield this section and all subsections (and subsubsections, etc., recursively) in the order they would appear in the file. To iterate over only direct subsections, just use `for subsection in section.subsections`. """
        yield self
        for s in self.subsections:
            yield from s

    def __str__(self):
        return f"{self.__class__.__name__}"

    def __repr__(self):
        return self.__str__()

    def set_bytes(self, offset: int | str, value: bytes):
        self._edit()
        if isinstance(offset, str):
            offset = self.offsets[offset]
        l = len(value)
        self._data[offset:offset+l] = value

    def get_bytes(self, offset: int | str, length: int):
        if isinstance(offset, str):
            offset = self.offsets[offset]
        return self._data[offset:offset + length]

    def set_int(self, offset: int | str, value: int):
        self._edit()
        if isinstance(offset, str):
            offset = self.offsets[offset]
        pack_int_into(self._data, offset, value)

    def get_int(self, offset: int | str):
        if isinstance(offset, str):
            offset = self.offsets[offset]
        return unpack_int(self._data, offset)


class boma(Section):
    offsets = {
        **Section.offsets,
        "size": 8,  # only this section type has the size in a different place
        "subtype": 12,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtype = self.get_int("subtype")

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
Data = boma


class DataContainerSection(Section):
    """ Add methods for boma subsections """
    expected_subsections = {b"boma"}

    data_subtypes: dict[str, int] = {}
    """ Subtype name -> subtype number """
    numeric_data_offsets: dict[int, dict[str, int]] = {}
    """ Subtype number -> offset name -> offset. Anything not given offsets here is assumed to be a string container. """

    def data_subsection_of_subtype(self, subtype: str | int):
        if isinstance(subtype, str):
            subtype = self.data_subtypes[subtype]
        for s in self.subsections:
            if isinstance(s, Data) and s.subtype == subtype:
                return s  # assumes there's only one subsection with the specified subtype
        raise KeyError(self, subtype)

    def get_data_subsection_string(self, subtype: str | int):
        if isinstance(subtype, str):
            # if subtype given as int we will assume caller already knows what they're doing (or intentionally wants to bypass these checks e.g. for a section type unknown to the code)
            subtype_number = self.data_subtypes[subtype]
            if subtype_number in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a string")
        return self.data_subsection_of_subtype(subtype).get_string()

    def set_data_subsection_string(self, subtype: str | int, value: str):
        if isinstance(subtype, str):
            subtype_number = self.data_subtypes[subtype]
            if subtype_number in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a string")
        self.data_subsection_of_subtype(subtype).set_string(value)

    def get_data_subsection_int(self, subtype: str | int, offset: str | int):
        if isinstance(subtype, str):
            subtype_number = self.data_subtypes[subtype]
            if subtype_number not in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a numeric container")
            subtype = subtype_number
        if isinstance(offset, str):
            offset = self.numeric_data_offsets[subtype][offset]
        return self.data_subsection_of_subtype(subtype).get_int(offset)

    def set_data_subsection_int(self, subtype: str | int, offset: str | int, value: int):
        if isinstance(subtype, str):
            subtype_number = self.data_subtypes[subtype]
            if subtype_number not in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a numeric container")
            subtype = subtype_number
        if isinstance(offset, str):
            offset = self.numeric_data_offsets[subtype][offset]
        self.data_subsection_of_subtype(subtype).set_int(offset, value)

    def __str__(self):
        def f():
            for subsection in self.subsections:
                if isinstance(subsection, Data):
                    for subtype_name, subtype_number in self.data_subtypes.items():
                        if subtype_number == subsection.subtype:
                            if subtype_number in self.numeric_data_offsets:
                                yield f"\"{subtype_name}\": {{{", ".join(
                                    f"\"{offset_name}\": {subsection.get_int(offset)}"
                                    for offset_name, offset in self.numeric_data_offsets[subtype_number].items()
                                )}}}"
                            else:
                                yield f"\"{subtype_name}\": \"{subsection.get_string()}\""
                else:
                    yield subsection.__class__.__name__

        return (
            f"{self.__class__.__name__} {{"
            + ", ".join(f())
            + "}"
        )

    def __repr__(self):
        return self.__str__()

# don't know where these boma subtypes go because they aren't in my library
# listed as "book" type on vollink but not present in my library: 0x42,
# "unknown 64x4b hex string": 0x1f4,
# another "unknown 64x4b hex string": 0x1fe,
# "xml block (unknown utility)": 0x2bc,
# "xml block (unknown utility)": 0x3cc,

# don't know where this offset data goes
# numeric_data_offsets = {
#     "video": {
#         "height": 20,
#         "width": 24,
#         "framerate": 64,
#     },
# }

class hsma(Section):
    offsets = {
        **Section.offsets,
        "total_size": 8,
    }
    expected_subsections = {
        b"hfma",
        b"plma",
        b"lama",
        b"lAma",
        b"ltma",
        b"lPma",
        b"LPma",
    }


register_section_class(hsma)
Boundary = hsma


class hfma(Section):  # inner hfma only, not outer hfma which is Library
    offsets = {
        **Section.offsets,
    }


register_section_class(hfma)
Envelope = hfma


class plma(DataContainerSection):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }

    data_subtypes = {
        # "unknown", "found under plma": 0x1f6,
        "managed_media_folder": 0x1f8,
        # listed as "book" type on vollink but not this type in my library: 0x1fc,
        # listed as "book" type on vollink but not this type in my library: 0x1fd,
        # present in my library, not listed on vollink: 0x1ff,
        # listed as "book" type on vollink but not this type in my library: 0x200,
    }


register_section_class(plma)
LibraryMaster = plma


class lama(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    expected_subsections = {b"iama"}


register_section_class(lama)
AlbumList = lama


class iama(DataContainerSection):
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
    }

    data_subtypes = {
        "name": 0x12c,
        "artist": 0x12d,
        "artist": 0x12e,  # duplicate name on vollink?
    }


register_section_class(iama)
Album = iama


class lAma(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    expected_subsections = {b"iAma"}


register_section_class(lAma)
AristList = lAma


class iAma(DataContainerSection):
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
    }

    data_subtypes = {
        # present in my library: 0x190,
        # present in my library: 0x191,
        "xml_artwork_url": 0x192,
    }


register_section_class(iAma)
Artist = iAma


class ltma(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    expected_subsections = {b"itma"}


register_section_class(ltma)
TrackList = ltma


class itma(DataContainerSection):
    offsets = {
        **Section.offsets,
        "subsection_count": 12,
        # todo many of these fields are not 4 bytes
        "love_or_dislike": 62,
        "stars": 65,
        "movements_in_work": 86,
        "movements_of_work": 88,
        "track_number": 160,
        "year": 167,
    }

    data_subtypes = {
        "track_numerics": 0x1,
        "title": 0x2,
        "album": 0x3,
        "artist": 0x4,
        "genre": 0x5,
        "kind": 0x6,
        # "not sure" on vollink: 0x7,
        "comment": 0x8,
        # present in my library: 0xb,
        "composer": 0xc,
        "grouping": 0xe,
        "episode_comment": 0x12,
        "episode_synopsis": 0x16,
        "plays_skips": 0x17,
        "series_title": 0x18,
        "episode_number": 0x19,
        "track_album_artist": 0x1b,
        "series": 0x1c,
        # "xml block (unknown utility)": 0x1d,
        "title_sort": 0x1e,
        "album_sort": 0x1f,
        "artist_sort": 0x20,
        "album_artist_sort": 0x21,
        "composer_sort": 0x22,
        "video": 0x24,
        "copyright_holder": 0x2b,
        # another "not sure" : 0x2e,
        "series_synopsis": 0x33,
        "flavor_string": 0x34,
        # "xml block (unknown utility)": 0x36,
        # "xml block (unknown utility)": 0x38,
        "purchaser_email": 0x3b,
        "purchaser_name": 0x3c,
        "work_name": 0x3f,
        "movement_name": 0x40,
        # present in my library: 0x43,
        "series_title": 0x12f,
    }
    numeric_data_offsets = {
        0x1: {
            "bit_rate": 108,
            "date_added": 112,
            "date_modified": 148,
            "normalization": 152,
            "song_duration": 176,
            "file size": 316,
        },
        0x17: {
            "last_played": 28,
            "plays": 32,
            "last_skipped": 48,
            "skips": 52
        }
    }

    LOVE = 2
    DISLIKE = 3
    NOT_LOVE_OR_DISLIKE = 0

    STARS_0 = 0
    STARS_1 = 20
    STARS_2 = 40
    STARS_3 = 60
    STARS_4 = 80
    STARS_5 = 100


register_section_class(itma)
Track = itma


class lPma(Section):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
        "playlist_length": 16,
        "date_created": 22,
        "date_modified": 138,
    }
    expected_subsections = {b"lpma"}


register_section_class(lPma)
PlaylistList = lPma


class lpma(DataContainerSection):
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
    }

    data_subtypes = {
        "playlist_name": 0xc8,
        # "unknown", "found under lpma": 0xc9,
        # "unknown", "found under lpma": 0xca,
        # "xml block (unknown utility)": 0xcd,
        "ipfa": 0xce,
    }
    numeric_data_offsets = {
        0xce: {
            # todo
        }
    }


register_section_class(lpma)
Playlist = lpma


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
        "song_count": 68,
        "playlist_count": 72,
        "album_count": 76,
        "artist_count": 80,
        "date_modified": 100,
    }
    check_signature = False  # hfma signature is registered for the inner one

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
