from collections import defaultdict
from enum import IntEnum
import random
from typing import override

from .binary_object import BinaryObjectParentSection, String, boma
from .section import Section
from .shared_enums import StarRating, SuggestionFlag


class bomaAlbum(boma):
    subsection_class_by_subtype = {
        0x12C: String,
        0x12D: String,
        0x12E: String,
    }


class StarRatingInheritance(IntEnum):
    DIRECT = 0x1
    INHERITED = 0x20


class iama(BinaryObjectParentSection):
    expected_signature = b"iama"
    subsection_class = bomaAlbum
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
        "id_album": 16,
        "id_first_track": 32,
        "star_rating": 40,
        "star_rating_inheritance": 41,
        "suggestion_flag": 42,
        "id_album_2": 64,
        "date_modified_suggestion_flag": 96,
        "date_last_played": 100,
        "id_apple_music_album": 104,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "id_album": 8,
        "id_first_track": 8,
        "star_rating": 1,
        "star_rating_inheritance": 1,
        "suggestion_flag": 1,
        "id_album_2": 8,
    })
    offset_int_enums = {
        "star_rating": StarRating,
        "star_rating_inheritance": StarRatingInheritance,
        "suggestion_flag": SuggestionFlag,
    }
    default_values = {
        "size": 140
    }

    data_subtypes = {
        "name": 0x12c,
        "title": 0x12c,  # alias for the previous
        "artist": 0x12d,
        "album_artist": 0x12e,
    }
    data_subtype_aliases = {
        "title",
    }

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
        a = super().from_scratch(initial_values, initial_children)
        # experimentally this does not seem necessary, doesn't hurt either though
        if a.get_bytes("id_album", 8) == b"\x00"*8:
            a.set_bytes("id_album", random.randbytes(8))
        return a


class lama(Section):
    expected_signature = b"lama"
    subsection_class = iama
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    default_values = {
        "size": 48
    }
