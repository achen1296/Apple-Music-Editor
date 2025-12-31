from collections import defaultdict
from enum import IntEnum
from io import BytesIO
from typing import Type, override

from .section import BigEndianSection
from .shared_enums import SuggestionFlag


def negate_comparison_method(i: int):
    return i | 0x_02_00_00_00


class BooleanField(IntEnum):
    ALBUM_ARTWORK = 0x25
    CHECKED = 0x1D
    COMPILATION = 0x1F
    PURCHASED = 0x29


class BooleanComparison(IntEnum):
    IS_TRUE = 0x1
    IS_FALSE = negate_comparison_method(IS_TRUE)


class NumericField(IntEnum):
    STAR_RATING_ALBUM = 0x5A
    BIT_RATE = 0x5
    BPM = 0x23
    DISC_NUMBER = 0x18
    MOVEMENT_NUMBER = 0xA1
    PLAYS = 0x16
    STAR_RATING_TRACK = 0x19
    SAMPLE_RATE = 0x6
    FILE_SIZE = 0x1C
    SKIPS = 0x44
    SONG_DURATION = 0xD
    TIME = SONG_DURATION  # alias matching name in GUI
    TRACK_NUMBER = 0xB
    YEAR = 0x7


class NumericComparison(IntEnum):
    IS = 0x1
    IS_NOT = negate_comparison_method(IS)
    IS_GREATER_THAN = 0x10
    IS_LESS_THAN = 0x40
    IS_IN_THE_RANGE = 0x100


class StarRatingSmartPlaylistArgument(IntEnum):
    STARS_0 = -20  # this one is different from StarRating
    STARS_1 = 20
    STARS_2 = 40
    STARS_3 = 60
    STARS_4 = 80
    STARS_5 = 100


NUMERIC_FIELD_ARGUMENT_VALUE_ENUMS: dict[NumericField, Type[IntEnum]] = {
    NumericField.STAR_RATING_ALBUM: StarRatingSmartPlaylistArgument,
    NumericField.STAR_RATING_TRACK: StarRatingSmartPlaylistArgument,
}


class DateField(IntEnum):
    DATE_ADDED = 0x10
    DATE_MODIFIED = 0xA
    DATE_LAST_PLAYED = 0x17
    DATE_LAST_SKIPPED = 0x45


class DateComparison(IntEnum):
    IS_IN_THE_RANGE = 0x100
    IS = IS_IN_THE_RANGE
    IS_NOT = negate_comparison_method(IS)
    IS_GREATER_THAN = 0x10
    IS_AFTER = IS_GREATER_THAN  # alias matching name in GUI
    IS_LESS_THAN = 0x40
    IS_BEFORE = IS_LESS_THAN  # alias matching name in GUI
    IS_IN_THE_LAST = 0x200
    IS_NOT_IN_THE_LAST = negate_comparison_method(IS_IN_THE_LAST)


class EnumField(IntEnum):
    SUGGESTION_FLAG_ALBUM = 0x9C
    ALBUM_FAVORITE = SUGGESTION_FLAG_ALBUM  # alias matching name in GUI

    SUGGESTION_FLAG_TRACK = 0x9A
    TRACK_FAVORITE = SUGGESTION_FLAG_TRACK
    FAVORITE = SUGGESTION_FLAG_TRACK  # alias matching name in GUI

    CLOUD_STATUS = 0x86
    LOCATION = 0x85
    MEDIA_KIND = 0x3C


class EnumComparison(IntEnum):
    IS = 0x1
    IS_NOT = negate_comparison_method(IS)

    LOCATION_IS = 0x400
    LOCATION_IS_NOT = negate_comparison_method(LOCATION_IS)


class CloudStatus(IntEnum):
    MATCHED = 2
    PURCHASED = 1
    UPLOADED = 3
    INELIGIBLE = 4
    REMOVED = 5
    ERROR = 6
    DUPLICATE = 7
    APPLE_MUSIC = 8
    NO_LONGER_AVAILABLE = 9
    NOT_UPLOADED = 10


class Location(IntEnum):
    ON_COMPUTER = 1
    ICLOUD = 16


class MediaKind(IntEnum):
    MUSIC = 0x1
    MUSIC_VIDEO = 0x20
    MOVIES = 0x2
    TV_SHOWS = 0x40
    PODCASTS = 0x5
    AUDIO_BOOKS = 0x8
    VOICE_MEMOS = 0x_10_00_00
    ITUNES_EXTRAS = 0x_01_00_00
    HOME_VIDEOS = 0x_04_00


ENUM_FIELD_ARGUMENT_VALUE_ENUMS: dict[EnumField, Type[IntEnum]] = {
    EnumField.SUGGESTION_FLAG_ALBUM: SuggestionFlag,
    EnumField.SUGGESTION_FLAG_TRACK: SuggestionFlag,
    EnumField.CLOUD_STATUS: CloudStatus,
    EnumField.LOCATION: Location,
    EnumField.MEDIA_KIND: MediaKind,
}


class StringField(IntEnum):
    ALBUM = 0x3
    ALBUM_ARTIST = 0x47
    ARTIST = 0x4
    CATEGORY = 0x37
    COMMENTS = 0xE
    COMPOSER = 0x12
    DESCRIPTION = 0x36
    GENRE = 0x8
    GROUPING = 0x27
    KIND = 0x9
    MOVEMENT_NAME = 0xA0
    SORT_ALBUM = 0x4F
    SORT_ALBUM_ARTIST = 0x51
    SORT_ARTIST = 0x50
    SORT_COMPOSER = 0x52
    SORT_SHOW = 0x53
    SORT_TITLE = 0x4E
    TITLE = 0x2
    VIDEO_RATING = 0x59
    WORK_NAME = 0x9F


class StringComparison(IntEnum):
    CONTAINS = 0x_01_00_00_02
    DOES_NOT_CONTAIN = negate_comparison_method(CONTAINS)
    IS = 0x_01_00_00_01
    IS_NOT = negate_comparison_method(IS)
    BEGINS_WITH = 0x_01_00_00_04
    ENDS_WITH = 0x_01_00_00_08


class PlaylistField(IntEnum):
    PLAYLIST = 0x28


class PlaylistComparison(IntEnum):
    IS = 0x1
    IS_NOT = negate_comparison_method(IS)


AnyField = BooleanField | NumericField | DateField | EnumField | StringField | PlaylistField
AnyComparison = BooleanComparison | NumericComparison | DateComparison | EnumComparison | StringComparison | PlaylistComparison

FIELD_INT_ENUMS: list[Type[IntEnum]] = [BooleanField, NumericField, DateField, EnumField, StringField, PlaylistField,]
COMPARISON_INT_ENUMS: dict[Type[IntEnum], Type[IntEnum]] = {
    BooleanField: BooleanComparison,
    NumericField: NumericComparison,
    DateField: DateComparison,
    EnumField: EnumComparison,
    StringField: StringComparison,
    PlaylistField: PlaylistComparison,
}
ARGUMENTS_USED: dict[Type[IntEnum], list[str]] = {
    BooleanField: [],
    NumericField: ["argument_0", "argument_3"],
    DateField: [f"argument_{i}" for i in range(0, 4)],
    EnumField: ["argument_0", "argument_3"],
    StringField: [],
    PlaylistField: ["argument_0", "argument_3"],
}

MAX_ARGUMENTS = 8


class SmartPlaylistRule(BigEndianSection):
    fixed_size = 56  # must read this far to get offset 54, 2 bytes to determine how long the rest is
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "field": 0,
        "comparison_method": 4,
        "arguments_size": 54,

        "argument_string": 56,
        # these are intentionally overlapping with "argument_string"
        **{
            f"argument_{i}": 56 + i*8
            for i in range(0, MAX_ARGUMENTS)  # could fit up to 8 8-byte chunks even though only 4 actually get used
        },
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "arguments_size": 2,
        **{
            f"argument_{i}": 8
            for i in range(0, MAX_ARGUMENTS)
        },
    })
    # offset_int_enums = {}
    # to be set depending on the actual values encountered

    def __init__(self, data: BytesIO, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        arg_length = self.get_int("arguments_size")
        self._data += data.read(arg_length)
        assert self.fixed_size is not None and self.size == self.fixed_size + arg_length

        # figure out field type and arguments in use
        # cannot just look for the default values to determine arguments in use because some actual values collide with them

        field = self.get_int("field")
        for e in FIELD_INT_ENUMS:
            try:
                field = e(field)
            except ValueError:
                pass

        if not isinstance(field, IntEnum):
            print(f"warning: unknown smart playlist field {field}")
            self.int_arguments_in_use = [
                f"argument_{i}"
                for i in range(0, MAX_ARGUMENTS)
            ]  # just so they all get included in __str__
            self.string_argument_in_use = False # may not be safe to decode for arbitrary data
            return

        self.offset_int_enums = {
            "field": field.__class__,
            "comparison_method": COMPARISON_INT_ENUMS[field.__class__],
        }

        if isinstance(field, EnumField):
            self.offset_int_enums["argument_1"] = self.offset_int_enums["argument_3"] = ENUM_FIELD_ARGUMENT_VALUE_ENUMS[field]

        self.int_arguments_in_use = ARGUMENTS_USED[field.__class__]
        self.string_argument_in_use = isinstance(field, StringField)

    def get_string(self):
        if not self.string_argument_in_use:
            raise ValueError("this smart playlist rule is not supposed to have a string argument")
        return self._data[self.offsets["argument_string"]:].decode("utf_16_be")

    def set_string(self, value: str):
        if not self.string_argument_in_use:
            raise ValueError("this smart playlist rule is not supposed to have a string argument")
        self._data[self.offsets["argument_string"]:] = value.encode("utf_16_be")

    @override
    def as_dict(self) -> dict:
        d = {
            offset_name: self.get_int(offset_name)
            for offset_name in [
                "field",
                "comparison_method",
                "arguments_size"
            ] + self.int_arguments_in_use
        }
        if self.string_argument_in_use:
            d["argument_string"] = self.get_string()
        return d
