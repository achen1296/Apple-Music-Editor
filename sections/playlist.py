from collections import defaultdict
from enum import IntEnum

from .shared_enums import StarRating, SuggestionFlag

from .binary_object import DataContainerSection, RawStringUTF8, String, boma
from .section import Section
from .smart_playlist_options import SmartPlaylistOptions
from .smart_playlist_rules_list import SLst


class ipfa(Section):
    expected_signature = b"ipfa"
    offsets = {
        **Section.offsets,
        "id_ipfa": 12,
        "id_track": 20,
        "id_ipfa_2": 44,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "id_ipfa": 8,
        "id_track": 8,
        "id_ipfa_2": 8,
    })


class bomaPlaylist(boma):
    subsection_class_by_subtype = {
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


class lpma(DataContainerSection):
    expected_signature = b"lpma"
    subsection_class = bomaPlaylist
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
        "tracks_total": 16,
        "date_created": 22,
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

    data_subtypes = {
        "name": 0xc8,
        "title": 0xc8,  # alias for the previous
        "smart_playlist_rules": 0xc9,
        "smart_playlist_options": 0xca,
        "plist_generated_artwork_uuids": 0xcd,
        "playlist_item": 0xce,
    }
    data_subtype_aliases = {
        "title",
    }


class lPma(Section):
    expected_signature = b"lPma"
    subsection_class = lpma
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
