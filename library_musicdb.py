from collections import defaultdict
import os
import zlib
from datetime import datetime, timezone
from io import SEEK_CUR, BytesIO
from pathlib import Path
from typing import Callable, Iterable, Iterator, Type, override

from Crypto.Cipher import AES

from byte_util import pack_int, pack_int_into, show_control_chars, unpack_int

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


def datetime_to_int(d: datetime | None = None):
    # +2082844800 to convert Unix epoch (Jan 1 1970) to Mac epoch (Jan 1 1904)
    if d is None:
        d = datetime.now(timezone.utc)
    return int(d.timestamp()) + 2082844800


def int_to_datetime(i: int):
    i -= 2082844800
    return datetime.fromtimestamp(i, timezone.utc)


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
    offset_int_sizes: defaultdict[str, int] = defaultdict(lambda: 4)
    """ Assume size 4 bytes if not specified (since that is the most common) """
    expected_subsections: set[bytes] = set()
    check_signature = True

    def __init__(self, data: BytesIO, check_signature=True):
        self._signature = None

        self._edited = False
        self._changed_size = False
        self._updated_size_after_change = True
        self._subsection_count_changed = False

        start_offset = data.tell()

        # read this section
        self._data = bytearray(data.read(self.offsets["size"] + self.offset_int_sizes["size"]))
        self._data += data.read(self.size_from_data - (self.offsets["size"] + self.offset_int_sizes["size"]))
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
            self._signature = self._data[self.offsets["signature"]:self.offsets["signature"] + self.offset_int_sizes["signature"]]
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
        if self.offsets["total_size"] >= 0 and any(s._changed_size or s._subsection_count_changed for s in self):
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
            self.set_int("date_modified", datetime_to_int())
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

    def as_dict(self) -> dict:
        return {
            offset_name: self.get_int(offset_name)
            for offset_name in self.offsets
            if self.offsets[offset_name] >= 0
        }

    def __str__(self):
        return f"<{self.__class__.__name__} {self.as_dict()}>"

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

    def set_int(self, key: str | tuple[int, int], value: int):
        self._edit()
        if isinstance(key, str):
            offset = self.offsets[key]
            size = self.offset_int_sizes[key]
        else:
            offset, size = key
        pack_int_into(self._data, offset, value, size=size)

    def get_int(self, key: str | tuple[int, int]):
        if isinstance(key, str):
            offset = self.offsets[key]
            size = self.offset_int_sizes[key]
        else:
            offset, size = key
        return unpack_int(self._data, offset, size=size)


class boma(Section):
    offsets = {
        **Section.offsets,
        "size": 8,  # only this section type has the size in a different place
        "subtype": 12,
    }

    @override
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtype = self.get_int("subtype")

    def get_string(self):
        """ See `set_string` """
        string_format = self.get_int((20, 4))
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

        string_format = self.get_int((20, 4))
        if string_format == 1:
            self._data[36:] = value.encode("utf_16_le")
            # superclass will take care of the section length
            self.set_int((24, 4), self.size - 36)
        elif string_format == 2:
            self._data[36:] = value.encode("utf_8")
            self.set_int((24, 4), self.size - 36)
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
    numeric_data_sizes: defaultdict[int, defaultdict[str, int]] = defaultdict(lambda: defaultdict(lambda: 4))
    """ Subtype number -> offset name -> size. Anything not given offsets here is assumed to be a string container. """

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

    def get_data_subsection_int(self, subtype: str | int, key: str | tuple[int, int]):
        if isinstance(subtype, str):
            subtype_number = self.data_subtypes[subtype]
            if subtype_number not in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a numeric container")
            subtype = subtype_number
        if isinstance(key, str):
            key = (
                self.numeric_data_offsets[subtype][key],
                self.numeric_data_sizes[subtype][key]
            )
        return self.data_subsection_of_subtype(subtype).get_int(key)

    def set_data_subsection_int(self, subtype: str | int, key: str | tuple[int, int], value: int):
        if isinstance(subtype, str):
            subtype_number = self.data_subtypes[subtype]
            if subtype_number not in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a numeric container")
            subtype = subtype_number
        if isinstance(key, str):
            key = (
                self.numeric_data_offsets[subtype][key],
                self.numeric_data_sizes[subtype][key]
            )
        self.data_subsection_of_subtype(subtype).set_int(key, value)

    @override
    def as_dict(self):
        d = super().as_dict()
        for subsection in self.subsections:
            if isinstance(subsection, Data):
                for subtype_name, subtype_number in self.data_subtypes.items():
                    if subtype_number == subsection.subtype:
                        if subtype_number in self.numeric_data_offsets:
                            d[subtype_name] = {
                                offset_name: subsection.get_int((offset, self.numeric_data_sizes[subtype_number][offset_name]))
                                for offset_name, offset in self.numeric_data_offsets[subtype_number].items()
                            }
                        else:
                            d[subtype_name] = subsection.get_string()
        return d

# don't know where these boma subtypes go because they aren't in my library
# listed as "book" type on vollink but not present in my library: 0x42,
# "unknown 64x4b hex string": 0x1f4,
# another "unknown 64x4b hex string": 0x1fe,
# "xml block (unknown utility)": 0x2bc,
# "xml block (unknown utility)": 0x3cc,


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
        # some more known data listed here in vollink but none interesting to edit
    }


register_section_class(hfma)
Envelope = hfma


class plma(DataContainerSection):
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
        # some more known data listed here in vollink but none interesting to edit
    }

    data_subtypes = {
        # "unknown", "found under plma": 0x1f6,
        "media_folder_uri": 0x1f8,
        "imported_itl_file": 0x1fc,
        # listed as "book" type on vollink but not this type in my library: 0x1fd,
        # present in my library, not listed on vollink: 0x1ff,
        "media_folder": 0x200,
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
        "album_id": 16,
        "first_track_id": 32,
        "last_played": 100,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "album_id": 8,
        "first_track_id": 8,
    })

    data_subtypes = {
        "name": 0x12c,
        "artist": 0x12d,
        "album_artist": 0x12e,
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
        "artist_id": 16,
        "artist_store_id": 52,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "artist_id": 8,
    })

    data_subtypes = {
        "artist": 0x190,
        "artist_sort": 0x191,
        "artwork_url_plist": 0x192,
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
        "track_id": 16,
        "skip_when_shuffling": 30,
        "album_is_compilation": 38,
        "disabled": 42,
        "remember_playback_position": 50,
        "show_composer_in_all_views": 51,
        "use_work_and_movement": 52,
        "purchased": 58,
        "content_rating": 59,
        "suggestion_flag": 62,
        "rating": 65,
        "bpm": 82,
        "disc": 84,
        "total_movements": 86,
        "movement": 88,
        "total_discs": 90,
        "volume_adjustment": 92,
        "start_pos": 148,
        "stop_pos": 152,
        "track_number": 160,
        "year": 168,
        "album_id": 172,
        "artist_id": 180,
        "artwork_id_low": 256,
        "artwork_id_high": 264,
        "track_id_2": 272,
        "date_suggestion_flag_changed": 336,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "track_id": 8,
        "skip_when_shuffling": 1,
        "album_is_compilation": 1,
        "disabled": 1,
        "remember_playback_position": 1,
        "show_composer_in_all_views": 1,
        "use_work_and_movement": 1,
        "purchased": 1,
        "content_rating": 1,
        "suggestion_flag": 2,
        "rating": 1,
        "bpm": 2,
        "disc": 2,
        "total_movements": 2,
        "movement": 2,
        "total_discs": 2,
        "track_number": 2,
        "album_id": 8,
        "artist_id": 8,
        "artwork_id_low": 8,
        "artwork_id_high": 8,
        "track_id_2": 8,
    })

    data_subtypes = {
        "track_numerics": 0x1,
        "title": 0x2,
        "album": 0x3,
        "artist": 0x4,
        "genre": 0x5,
        "kind": 0x6,
        "equalizer": 0x7,
        "comment": 0x8,
        "url": 0xb,
        "composer": 0xc,
        "grouping": 0xe,
        "episode_description": 0x12,
        "episode_synopsis": 0x16,
        "plays_skips": 0x17,
        "series_title": 0x18,
        "episode_number": 0x19,
        "album_artist": 0x1b,
        "content_rating": 0x1c,
        "asset_info_plist": 0x1d,
        "title_sort": 0x1e,
        "album_sort": 0x1f,
        "artist_sort": 0x20,
        "album_artist_sort": 0x21,
        "composer_sort": 0x22,
        "video": 0x24,
        "isrc": 0x2b,
        "copyright": 0x2e,
        "series_synopsis": 0x33,
        "flavor_string": 0x34,
        "artwork_plist": 0x36,
        "redownload_params_plist": 0x38,
        "purchaser_username": 0x3b,
        "purchaser_name": 0x3c,
        "work_name": 0x3f,
        "movement_name": 0x40,
        "file": 0x43,
        "series_title": 0x12f,
    }
    numeric_data_offsets = {
        0x1: {
            "sample_rate": 80,
            "file_folder_count": 92,
            "library_folder_count": 94,
            "artwork_count": 96,
            "artwork_total_size": 104,
            "bit_rate": 108,
            "date_added": 112,
            "lyrics_hash": 144,
            "date_modified": 148,
            "normalization": 152,
            "purchase_date": 156,
            "release_date": 160,
            "song_duration": 176,
            "file_size": 316,
        },
        0x17: {
            "track_id": 20,
            "last_played": 28,
            "plays": 32,
            # jsharkey13 has "play_count_2": 36 but I'm not sure what this means
            "last_skipped": 48,
            "skips": 52
            # jsharkey13 has "skip_count_2": 56 but I'm not sure what this means
        },
        0x24: {
            "height": 20,
            "width": 24,
            "framerate": 64,
        },
    }
    numeric_data_sizes = defaultdict(lambda: defaultdict(lambda: 4), {
        0x1: defaultdict(lambda: 4, {
            "file_folder_count": 2,
            "library_folder_count": 2,
            "artwork_count": 2,
        })
    })

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
    }
    expected_subsections = {b"lpma"}


register_section_class(lPma)
PlaylistList = lPma


class lpma(DataContainerSection):
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
        "total_tracks": 16,
        "date_created": 22,
        "playlist_id": 30,
        "date_modified": 138,
        "playlist_id_2": 280,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "playlist_id": 8,
        "playlist_id_2": 8,
    })

    data_subtypes = {
        "name": 0xc8,
        "smart_playlist_rules": 0xc9,
        "smart_playlist_options": 0xca,
        "generated_artwork_uuids_plist": 0xcd,
        "ipfa": 0xce,
    }
    numeric_data_offsets = {
        0xce: {},   # todo
        0xca: {},   # todo
        0xc9: {},   # todo
    }
    numeric_data_sizes = defaultdict(lambda: defaultdict(lambda: 4), {
        0xce: defaultdict(lambda: 4, {}),  # todo
        0xca: defaultdict(lambda: 4, {}),  # todo
        0xc9: defaultdict(lambda: 4, {}),  # todo
    })


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
    # this class does not maintain what would otherwise be its "total_size" (the length of the entire file) because that also depends on the encryption/compression process, so that's handled in `save_library_bytes`
    # however, I do make sure the modified date is set
    offsets = {
        **Section.offsets,
        "file_format_major_version": 12,
        "file_format_minor_version": 14,
        # "apple_music_version": 16, # this is a string which would currently break the code expecting ints only other than in boma
        "library_id": 48,
        "musicdb_file_type": 56,
        "song_count": 68,
        "playlist_count": 72,
        "album_count": 76,
        "artist_count": 80,
        # "max_crypt_size": 84, # handled in load/save_library_bytes
        "library_time_offset": 88,
        "date_modified": 100,
        "library_id_itunes": 108,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "file_format_major_version": 2,
        "file_format_minor_version": 2,
        "library_id": 8,
        "library_id_itunes": 8,
    })
    check_signature = False  # hfma signature is registered for the inner one

    @override
    def __init__(self, library: bytes | bytearray | Path | str = DEFAULT_LIBRARY_FILE):
        if isinstance(library, Path) or isinstance(library, str):
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
