from .binary_object import (DataContainerSection, RawStringUTF8,
                            RawStringUTF16, String, boma)
from .section import Section


class bomaLibraryMaster(boma):
    subsection_class_by_subtype = {
        # 0x1F6: ,
        # 0x1F6: ,
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
        # some more known data listed here in vollink but none interesting to edit
    }

    data_subtypes = {
        # "unknown", "found under plma": 0x1f6,
        "media_folder_uri": 0x1f8,
        "imported_itl_file": 0x1fc,
        # listed as "book" type on vollink but not this type in my library: 0x1fd,
        # present in my library, not listed on vollink: 0x1ff,
        "media_folder": 0x200,
    }
