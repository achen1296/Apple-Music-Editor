from collections import defaultdict
from io import BytesIO

from .binary_object import DataContainerSection, RawStringUTF8, String, boma
from .section import BigEndianSection, Section


class ipfa(Section):
    expected_signature = b"ipfa"
    offsets = {
        **Section.offsets,
        "ipfa_id": 12,
        "track_id": 20,
        "track_id_2": 44,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "ipfa_id": 8,
        "track_id": 8,
        "track_id_2": 8,
    })


class SmartPlaylistRule(BigEndianSection):
    fixed_size = 56  # must read this far to get offset 54, 2 bytes to determine how long the rest is
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "match_field": 0,
        "comparison_method": 4,
        "argument_length": 54,

        "string_argument": 56,
        # these are intentionally overlapping with "string_argument"
        "argument_1": 56,
        "argument_2": 64,
        "argument_3": 80,
        "argument_4": 88,
        "argument_5": 104,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "argument_length": 2,
        "argument_1": 8,
        "argument_2": 16,
        "argument_3": 8,
        "argument_4": 16,
        "argument_5": 20,
    })

    def __init__(self, data: BytesIO, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        arg_length = self.get_int("argument_length")
        self._data += data.read(arg_length)
        assert self.fixed_size is not None and self.size == self.fixed_size + arg_length


class SLst(Section):
    expected_signature = b"SLst"
    fixed_size = 136
    subsection_class = SmartPlaylistRule
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "signature": 0,
        "subsection_count": 11,
        "all_any": 15,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "all_any": 1,
    })


class SmartPlaylistOptions(Section):
    fixed_size = 112
    offsets: dict[str, int] = {
        # no **Section.offsets: does not have a typical size offset
        # todo
    }


class bomaPlaylist(boma):
    subsection_class_by_subtype = {
        0xCE: ipfa,
        0xCA: SmartPlaylistOptions,
        0xC9: SLst,
        0xC8: String,
        0xCD: RawStringUTF8,
    }


class lpma(DataContainerSection):
    expected_signature = b"lpma"
    subsection_class = bomaPlaylist
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
        "title": 0xc8,  # alias for the previous
        "smart_playlist_rules": 0xc9,
        "smart_playlist_options": 0xca,
        "generated_artwork_uuids_plist": 0xcd,
        "ipfa": 0xce,
    }


class lPma(Section):
    expected_signature = b"lPma"
    subsection_class = lpma
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
