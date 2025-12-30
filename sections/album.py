from collections import defaultdict

from .binary_object import DataContainerSection, String, boma
from .section import Section

class bomaAlbum(boma):
    subsection_class_by_subtype = {
        0x12C: String,
        0x12D: String,
        0x12E: String,
    }

class iama(DataContainerSection):
    expected_signature = b"iama"
    subsection_class = bomaAlbum
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
        "album_id": 16,
        "first_track_id": 32,
        "last_played": 100,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "album_id": 8,
        "first_track_id": 8,
    })

    data_subtypes = {
        "name": 0x12c,
        "artist": 0x12d,
        "album_artist": 0x12e,
    }


class lama(Section):
    expected_signature = b"lama"
    subsection_class = iama
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
