from collections import defaultdict

from .album import lama
from .artist import lAma
from .library_master import plma
from .playlist import lPma
from .section import Section
from .track import ltma
from .unknown import LPma


class hfma(Section):  # inner hfma only, not outer hfma which is Library
    expected_signature = b"hfma"
    offsets = {
        **Section.offsets,
        "file_size": 8,
        "file_format_major_version": 12,
        "file_format_minor_version": 14,
        # "apple_music_version_string": 16, # this is the only string not inside a section that is a child of boma, can't imagine wanting to edit this so I haven't written any code to handle this one case
        "id_library": 48,
        "musicdb_file_type": 56,
        "song_count": 68, # todo edit these counts if items are added/removed
        "playlist_count": 72,
        "album_count": 76,
        "artist_count": 80,
        "max_crypt_size": 84,
        "timezone_offset": 88,
        "id_apple_music_user": 92,
        "date_modified": 100,
        "id_itunes_library": 108,
    }
    offset_int_sizes =defaultdict(lambda:4, {
        "file_format_major_version": 2,
        "file_format_minor_version": 2,
        "id_library": 8,
        "id_apple_music_user_apple": 8,
        "id_itunes_library": 8,
    })
    default_values = {
        "size": 160
    }


class hsma(Section):
    expected_signature = b"hsma"
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subtype": 12,
    }
    default_values = {
        "size": 56
    }
    subsection_class_by_subtype = {
        3: hfma,
        6: plma,
        4: lama,
        5: lAma,
        1: ltma,
        2: lPma,
        17: LPma,
    }
