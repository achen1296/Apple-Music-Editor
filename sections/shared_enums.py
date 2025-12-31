from enum import IntEnum


class SuggestionFlag(IntEnum):
    DEFAULT = 0
    UNSET = 1 # GUI changes to this value after previously loved/disliked
    LOVE = 2
    SUGGEST_LESS = 3
    DISLIKE = SUGGEST_LESS # former name of this value


class StarRating(IntEnum):
    STARS_0 = 0
    STARS_1 = 20
    STARS_2 = 40
    STARS_3 = 60
    STARS_4 = 80
    STARS_5 = 100
