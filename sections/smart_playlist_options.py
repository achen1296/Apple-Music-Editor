from collections import defaultdict
from enum import IntEnum

from .section import Section


class LimitUnit(IntEnum):
    ITEMS = 0x3
    MINUTES = 0X1
    HOURS = 0x4
    MEGABYTES = 0x2
    GIGABYTES = 0x5


class LimitSelectionMethod(IntEnum):
    RANDOM = 0x02
    ALBUM = 0x06
    ARTIST = 0x07
    GENRE = 0x09
    TITLE = 0x05
    NAME = TITLE
    RATING = 0x1c  # named without highest/lowest/most/least because negation is a separate offset with other in between
    RECENTLY_PLAYED = 0x1a
    OFTEN_PLAYED = 0x19
    RECENTLY_ADDED = 0x15


class LimitSelectionMethodModifier(IntEnum):
    DEFAULT = 0
    HIGHEST = DEFAULT  # when expressed in English words, this one goes with rating
    MOST = DEFAULT  # and this one with the other fields, but of course it doesn't matter since it's the same value, this is just for readability

    NEGATED = 1
    LOWEST = NEGATED
    LEAST = NEGATED


class SmartPlaylistOptions(Section):
    fixed_size = 112
    offsets: dict[str, int] = {
        # no **Section.offsets: does not have a typical size offset
        "checkbox_live_updating": 0,
        "checkbox_enable_matching_rules": 1,
        "checkbox_enable_limit": 2,
        "limit_unit": 3,
        "limit_selection_method": 4,
        "limit_count": 8,
        "checkbox_match_only_checked_items": 12,
        "limit_selection_method_modifier": 13,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "checkbox_live_updating": 1,
        "checkbox_enable_matching_rules": 1,
        "checkbox_enable_limit": 1,
        "limit_unit": 1,
        "limit_selection_method": 1,
        "checkbox_match_only_checked_items": 1,
        "limit_selection_method_modifier": 1,
    })
    offset_int_enums = {
        "limit_unit": LimitUnit,
        "limit_selection_method": LimitSelectionMethod,
        "limit_selection_method_modifier": LimitSelectionMethodModifier,
    }
    default_values={
        "size": 112
    }