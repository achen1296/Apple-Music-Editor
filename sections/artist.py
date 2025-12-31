from collections import defaultdict

from .binary_object import (BinaryObjectParentSection, RawStringUTF8, String,
                            boma)
from .section import Section
from .shared_enums import StarRating, SuggestionFlag


class bomaArtist(boma):
    subsection_class_by_subtype = {
        0x190: String,
        0x191: String,
        0x192: RawStringUTF8,
    }


class iAma(BinaryObjectParentSection):
    expected_signature = b"iAma"
    subsection_class = bomaArtist
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
        "id_artist": 16,
        "id_apple_music_artist": 52,
        "date_modified_suggestion_flag": 60,
        "uuid_1_artwork": 64, # UUID is 16 bytes but unpack doesn't have a format specifier for that
        "uuid_2_artwork": 72,
        "id_artist_2": 80,
        "suggestion_flag": 101,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "id_artist": 8,
        "uuid_1_artwork": 8,
        "uuid_2_artwork": 8,
        "id_artist_2": 8,
        "suggestion_flag": 1,
    })
    offset_int_enums = {
        "suggestion_flag": SuggestionFlag,
    }

    data_subtypes = {
        "artist": 0x190,
        "sort_artist": 0x191,
        "plist_artwork_url": 0x192,
    }


class lAma(Section):
    expected_signature = b"lAma"
    subsection_class = iAma
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
