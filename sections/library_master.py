from collections import defaultdict

from .binary_object import (DataContainerSection, RawStringUTF8,
                            RawStringUTF16, String, boma)
from .section import Section


class _1F6(Section):
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        # ???
    }


class _1FF(Section):
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "library_id": 8,
        "library_id_2": 16,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "library_id": 8,
        "library_id_2": 8,
    })


class bomaLibraryMaster(boma):
    subsection_class_by_subtype = {
        0x1F6: _1F6,
        0x1FF: _1FF,
        0x1F8: String,
        0x1FC: RawStringUTF8,
        0x1FD: RawStringUTF16,
        0x200: RawStringUTF16,
    }


class plma(DataContainerSection):
    expected_signature = b"plma"
    subsection_class = bomaLibraryMaster
    offsets = {
        **Section.offsets,
        "subsection_count": 8,
        "checkbox_show_song_list_checkboxes": 24,
        "id_library": 58,
        "id_library_2": 92,
        "checkbox_keep_media_folder_organized": 148,
    }
    offset_int_sizes = defaultdict(lambda: 4, {
        "checkbox_show_song_list_checkboxes": 1,
        "id_library": 8,
        "id_library_2": 8,
        "checkbox_keep_media_folder_organized": 1,
    })

    data_subtypes = {
        # "unknown", "found under plma": 0x1f6,
        "media_folder_uri": 0x1f8,
        "imported_itl_file": 0x1fc,
        # listed as "book" type on vollink but not this type in my library: 0x1fd,
        # present in my library, not listed on vollink: 0x1ff,
        "media_folder_path": 0x200,
    }
