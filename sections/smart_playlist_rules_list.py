from enum import IntEnum
from .section import BigEndianSection
from .smart_playlist_rule import SmartPlaylistRule


class Conjunction(IntEnum):
    ALL = 0
    ANY = 1


class SLst(BigEndianSection):
    expected_signature = b"SLst"
    fixed_size = 136
    subsection_class = SmartPlaylistRule
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "signature": 0,
        "subsection_count": 8,
        "conjunction": 12,
        "all_any": 12,  # alias for previous
    }
    offset_aliases = {
        "all_any",
    }
    offset_int_enums = {
        "conjunction": Conjunction,
        "all_any": Conjunction,
    }
