from collections import defaultdict

from .binary_object import DataContainerSection, RawStringUTF8, String, boma
from .section import Section


class TrackNumerics(Section):
    fixed_size = 364
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "sample_rate": 60,
        "file_folder_count": 72,
        "library_folder_count": 74,
        "artwork_count": 76,
        "artwork_total_size": 84,
        "bit_rate": 88,
        "date_added": 92,
        "lyrics_hash": 124,
        "date_modified": 128,
        "normalization": 132,
        "purchase_date": 136,
        "release_date": 140,
        "song_duration": 156,
        "file_size": 296,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "file_folder_count": 2,
        "library_folder_count": 2,
        "artwork_count": 2,
    })


class TrackPlaysSkips(Section):
    fixed_size = 52
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "track_id": 0,
        "last_played": 8,
        "plays": 12,
        "true_play_count": 16,
        "last_skipped": 28,
        "skips": 32,
        "true_skip_count": 36,
    }


class Video(Section):
    fixed_size = 52  # not sure this is right, see readme
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "height": 0,
        "width": 4,
        "framerate": 48,
    }


class bomaTrack(boma):
    subsection_class_by_subtype = defaultdict(
        lambda: String,
        {
            0x1: TrackNumerics,
            0x17: TrackPlaysSkips,
            0x24: Video,

            0x36: RawStringUTF8,
            0x38: RawStringUTF8,
        }
    )


class itma(DataContainerSection):
    expected_signature = b"itma"
    subsection_class = bomaTrack
    offsets = {
        **Section.offsets,
        "subsection_count": 12,
        "track_id": 16,
        "skip_when_shuffling": 30,
        "album_is_compilation": 38,
        "disabled": 42,
        "remember_playback_position": 50,
        "show_composer_in_all_views": 51,
        "use_work_and_movement": 52,
        "purchased": 58,
        "content_rating": 59,
        "suggestion_flag": 62,
        "rating": 65,
        "bpm": 82,
        "disc": 84,
        "total_movements": 86,
        "movement": 88,
        "total_discs": 90,
        "volume_adjustment": 92,
        "start_pos": 148,
        "stop_pos": 152,
        "track_number": 160,
        "year": 168,
        "album_id": 172,
        "artist_id": 180,
        "artwork_id_low": 256,
        "artwork_id_high": 264,
        "track_id_2": 272,
        "date_suggestion_flag_changed": 336,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "track_id": 8,
        "skip_when_shuffling": 1,
        "album_is_compilation": 1,
        "disabled": 1,
        "remember_playback_position": 1,
        "show_composer_in_all_views": 1,
        "use_work_and_movement": 1,
        "purchased": 1,
        "content_rating": 1,
        "suggestion_flag": 2,
        "rating": 1,
        "bpm": 2,
        "disc": 2,
        "total_movements": 2,
        "movement": 2,
        "total_discs": 2,
        "track_number": 2,
        "album_id": 8,
        "artist_id": 8,
        "artwork_id_low": 8,
        "artwork_id_high": 8,
        "track_id_2": 8,
    })

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
        "asset_info_plist": 0x1d,
        "title_sort": 0x1e,
        "album_sort": 0x1f,
        "artist_sort": 0x20,
        "album_artist_sort": 0x21,
        "composer_sort": 0x22,
        "video": 0x24,
        "isrc": 0x2b,
        "copyright": 0x2e,
        "series_synopsis": 0x33,
        "flavor_string": 0x34,
        "artwork_plist": 0x36,
        "redownload_params_plist": 0x38,
        "purchaser_username": 0x3b,
        "purchaser_name": 0x3c,
        "work_name": 0x3f,
        "movement_name": 0x40,
        "file": 0x43,
        "series_title": 0x12f,
    }


class ltma(Section):
    expected_signature = b"ltma"
    subsection_class = itma
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
