from collections import defaultdict
from enum import IntEnum
import random
from typing import override

from .binary_object import (BinaryObjectParentSection, RawStringUTF8, String, StringPreferUTF8,
                            boma)
from .section import Section
from .shared_enums import StarRating, SuggestionFlag


class TrackNumerics(Section):
    fixed_size = 364
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "global_counter": 0,
        "sample_rate": 60,
        "file_folder_count": 72,
        "library_folder_count": 74,
        "artwork_count": 76,
        "artwork_total_size": 84,
        "bit_rate": 88,
        "date_added": 92,
        "date_modified": 128,
        "normalization": 132,
        "date_purchased": 136,
        "date_released": 140,
        "song_duration": 156,
        "id_apple_music_album": 160,
        "id_apple_music_artist": 168,
        "id_apple_music_album_artist": 208,
        "file_size": 296,
        "id_apple_music_song": 304,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "file_folder_count": 2,
        "library_folder_count": 2,
        "artwork_count": 2,
    })
    default_values = {
        "size": 364
    }


class TrackPlaysSkips(Section):
    fixed_size = 52
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "id_track": 0,
        "date_last_played": 8,
        "play_count": 12,
        "true_play_count": 16,
        "date_first_played": 20,
        "date_last_skipped": 28,
        "skip_count": 32,
        "true_skip_count": 36,
    }
    default_values = {
        "size": 52
    }


class Video(Section):
    fixed_size = 52  # not sure this is right, see readme
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "height": 0,
        "width": 4,
        "framerate": 48,
    }
    default_values = {
        "size": 52  # not sure this is right, see readme
    }


class bomaTrack(boma):
    subsection_class_by_subtype = defaultdict(
        lambda: String,
        {
            0x1: TrackNumerics,
            0x17: TrackPlaysSkips,
            0x24: Video,

            0xB: StringPreferUTF8,

            0x36: RawStringUTF8,
            0x38: RawStringUTF8,
        }
    )


class Downloaded(IntEnum):
    NOT_DOWNLOADED = 3
    DOWNLOADED = 1


class ContentRating(IntEnum):
    DEFAULT = 0
    EXPLICIT = 1
    CLEAN = 2
    PARENT_GUIDANCE = 4  # ?


class itma(BinaryObjectParentSection):
    expected_signature = b"itma"
    subsection_class = bomaTrack
    offsets = {
        **Section.offsets,
        "subsection_count": 12,
        "id_track": 16,
        "global_counter": 24,
        "checkbox_skip_when_shuffling": 30,
        "checkbox_album_is_compilation": 38,
        "checkbox_disabled": 42,
        "checkbox_remember_playback_position": 50,
        "checkbox_show_composer_in_all_views": 51,
        "checkbox_use_work_and_movement": 52,
        "downloaded": 57,
        "purchased": 58,
        "content_rating": 59,
        "suggestion_flag": 62,
        "star_rating": 65,
        "bpm": 82,
        "beats_per_minute": 82,  # alias for previous
        "disc_number": 84,
        "movement_total": 86,
        "movement_number": 88,
        "disc_total": 90,
        "volume_adjustment": 92,
        "track_total": 116,
        "playback_start_pos": 148,
        "playback_stop_pos": 152,
        "track_number": 160,
        "year": 168,
        "id_album": 172,
        "id_artist": 180,
        "id_apple_music_artist": 188,
        "uuid_1_artwork": 256,  # UUID is 16 bytes but unpack doesn't have a format specifier for that
        "uuid_2_artwork": 264,
        "id_track_2": 272,
        "date_suggestion_flag_modified": 336,
        "date_added_most_recent_track": 352,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "id_track": 8,
        "checkbox_skip_when_shuffling": 1,
        "checkbox_album_is_compilation": 1,
        "checkbox_disabled": 1,
        "checkbox_remember_playback_position": 1,
        "checkbox_show_composer_in_all_views": 1,
        "checkbox_use_work_and_movement": 1,
        "downloaded": 1,
        "purchased": 1,
        "content_rating": 1,
        "suggestion_flag": 2,
        "star_rating": 1,
        "bpm": 2,
        "beats_per_minute": 2,
        "disc_number": 2,
        "movement_total": 2,
        "movement_number": 2,
        "disc_total": 2,
        "track_number": 2,
        "track_total": 2,
        "id_album": 8,
        "id_artist": 8,
        "uuid_1_artwork": 8,
        "uuid_2_artwork": 8,
        "id_track_2": 8,
    })
    offset_aliases = {
        "beats_per_minute",
    }
    offset_int_enums = {
        "downloaded": Downloaded,
        "content_rating": ContentRating,
        "suggestion_flag": SuggestionFlag,
        "star_rating": StarRating,
    }
    default_values = {
        "size": 376
    }

    data_subtypes = {
        "track_numerics": 0x1,
        "name": 0x2,
        "title": 0x2,  # alias for the previous
        "album": 0x3,
        "artist": 0x4,
        "genre": 0x5,
        "kind": 0x6,
        "equalizer": 0x7,
        "comment": 0x8,
        "url": 0xb,
        "composer": 0xc,
        "grouping": 0xe,
        "episode_description": 0x12,
        "episode_synopsis": 0x16,
        "plays_skips": 0x17,
        "series_title": 0x18,
        "episode_number": 0x19,
        "album_artist": 0x1b,
        "content_rating": 0x1c,
        "plist_asset_info": 0x1d,
        "sort_title": 0x1e,
        "sort_album": 0x1f,
        "sort_artist": 0x20,
        "sort_album_artist": 0x21,
        "sort_composer": 0x22,
        "video": 0x24,
        "isrc": 0x2b,
        "copyright": 0x2e,
        "series_synopsis": 0x33,
        "flavor_string": 0x34,
        "plist_artwork": 0x36,
        "plist_redownload_params": 0x38,
        "purchaser_username": 0x3b,
        "purchaser_name": 0x3c,
        "work": 0x3f,
        "movement_name": 0x40,
        "file": 0x43,
        "series_title": 0x12f,
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
        t = super().from_scratch(initial_values, initial_children)

        # experimentally this does not seem necessary, doesn't hurt either though
        if t.get_bytes("id_track", 8) == b"\x00"*8:
            t.set_bytes("id_track", random.randbytes(8))
        return t


class ltma(Section):
    expected_signature = b"ltma"
    subsection_class = itma
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
    default_values = {
        "size": 92
    }
