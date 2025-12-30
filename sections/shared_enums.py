from enum import IntEnum


class SuggestionFlag(IntEnum):
    LOVE = 2
    DISLIKE = 3
    NOT_LOVE_OR_DISLIKE = 0


class StarRating(IntEnum):
    STARS_0 = 0
    STARS_1 = 20
    STARS_2 = 40
    STARS_3 = 60
    STARS_4 = 80
    STARS_5 = 100
