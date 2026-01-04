from collections import defaultdict
from enum import IntEnum
from io import BytesIO
import random
from typing import override

from date_util import datetime_to_int

from .smart_playlist_rule import SLst

from .binary_object import (BinaryObjectParentSection, RawStringUTF8, String,
                            boma)
from .section import Section
from .shared_enums import SuggestionFlag
from .smart_playlist_options import SmartPlaylistOptions


class ipfa(Section):
    expected_signature = b"ipfa"
    offsets = {
        **Section.offsets,
        "global_counter": 8,
        "id_ipfa": 12,
        "id_track": 20,
        "id_ipfa_2": 44,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "id_ipfa": 8,
        "id_track": 8,
        "id_ipfa_2": 8,
    })
    default_values = {
        "size": 68
    }

    @override
    @classmethod
    def from_scratch(cls, initial_values: dict[str | int | tuple[int, int], bytes | int | bool] = {}, initial_children: list[Section] = []):
        i = super().from_scratch(initial_values, initial_children)
        if i.get_bytes("id_ipfa", 8) == b"\x00"*8:
            i.set_bytes("id_ipfa", random.randbytes(8))
        return i


class bomaPlaylist(boma):
    subsection_class_by_subtype: dict[int, type[Section]] = {
        0xCE: ipfa,
        0xCA: SmartPlaylistOptions,
        0xC9: SLst,
        0xC8: String,
        0xCD: RawStringUTF8,
    }


class SpecialPlaylist(IntEnum):
    # remember to reverse endianness since this is 2 bytes!
    # although maybe it should just be 1 byte...
    NORMAL = 0
    DOWNLOADED = 0x_41_00
    MUSIC = 0x_04_00
    MUSIC_VIDEOS = 0x_2F_00
    TV_AND_MOVIES = 0x_40_00
    GENIUS = 0x_1A_00
    PURCHASED = 0x_13_00


class lpma(BinaryObjectParentSection):
    expected_signature = b"lpma"
    subsection_class = bomaPlaylist
    offsets: dict[str, int] = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
        "tracks_total": 16,
        "date_created": 22,
        "global_counter": 26,
        "id_playlist": 30,
        "id_parent_folder": 50,
        "special_playlist": 78,
        "date_modified": 138,
        "suggestion_flag": 223,
        "uuid_1_artwork": 263,
        "uuid_2_artwork": 271,
        "id_playlist_2": 280,
        "date_modified_suggestion_flag": 324,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "id_playlist": 8,
        "id_parent_folder": 8,
        "suggestion_flag": 1,
        "uuid_1_artwork": 8,
        "uuid_2_artwork": 8,
        "id_playlist_2": 8,
    })
    offset_int_enums = {
        "special_playlist": SpecialPlaylist,
        "suggestion_flag": SuggestionFlag,
    }
    default_values = {
        "size": 368
    }

    data_subtypes = {
        "name": 0xc8,
        "title": 0xc8,  # alias for the previous
        "smart_playlist_rules": 0xc9,
        "smart_playlist_options": 0xca,
        "plist_cover_artwork_recipe": 0xcd,
        "playlist_item": 0xce,
    }
    data_subtype_aliases = {
        "title",
    }

    @override
    def __init__(self, * args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_tracks_total = sum(
            isinstance(grandchild, ipfa)
            for child in self.children
            for grandchild in child.children
        )

    @override
    @classmethod
    def from_scratch(
        cls,
        initial_values:  dict[
            str | int | tuple[int, int],

            bytes | int | bool |
            dict[
                str | int | tuple[int, int],
                bytes | int | bool | str
            ]
        ] = {},
        initial_children: list[Section] = []
    ):
        p = super().from_scratch(initial_values, initial_children)

        if p.get_bytes("id_playlist", 8) == b"\x00"*8:
            p.set_bytes("id_playlist", random.randbytes(8))

        if p.get_int("date_created") == 0:
            p.set_int("date_created", datetime_to_int())

        return p

    @property
    @override
    def data(self):
        super().data

        # experimentally this does not seem necessary, doesn't hurt either though

        tracks_total: int = sum(
            isinstance(grandchild, ipfa)
            for child in self.children
            for grandchild in child.children
        )
        if self._last_tracks_total != tracks_total:
            self.set_int("tracks_total", tracks_total)
            self._last_tracks_total = tracks_total

        return self._data


class lPma(Section):
    expected_signature = b"lPma"
    subsection_class = lpma
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    default_values = {
        "size": 92
    }
