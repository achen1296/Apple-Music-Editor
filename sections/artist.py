from collections import defaultdict

from .binary_object import DataContainerSection, RawStringUTF8, String, boma
from .section import Section


class bomaArtist(boma):
    subsection_class_by_subtype = {
        0x190: String,
        0x191: String,
        0x192: RawStringUTF8,
    }


class iAma(DataContainerSection):
    expected_signature = b"iAma"
    subsection_class = bomaArtist
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subsection_count": 12,
        "artist_id": 16,
        "artist_store_id": 52,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        **Section.offset_int_sizes,
        "artist_id": 8,
    })

    data_subtypes = {
        "artist": 0x190,
        "artist_sort": 0x191,
        "artwork_url_plist": 0x192,
    }


class lAma(Section):
    expected_signature = b"lAma"
    subsection_class = iAma
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
    }
