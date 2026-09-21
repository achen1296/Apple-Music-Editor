from datetime import UTC, datetime
from xml.etree.ElementTree import Element, ElementTree
from xml.etree import ElementTree as ET

from library_musicdb import *


def write_itunes_xml(et: ElementTree, file="iTunes Music Library.xml"):
    with open(file, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(b'<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n')

        ET.indent(et, "\t")

        et.write(
            f,
            "utf8",
            False,  # no XML declaration since we manually inserted the doctype above, which required manually doing the declaration too
        )


def simplify_itunes_xml(file="iTunes Music Library.xml"):
    # this function was used to simplify an existing XML file to be a lot smaller while still serving as a good example
    itunes_xml = ElementTree()
    itunes_xml.parse(file)

    elements = itunes_xml.findall("./*/*")
    for i in range(len(elements)):
        e = elements[i]
        if e.text == "Tracks":
            tracks = elements[i+1]
            tracks[:] = tracks[:2]  # keep only first track (one key element and one dict element )
        if e.text == "Playlists":
            playlists = elements[i+1]
            playlists[:] = playlists[:1]  # keep only first playlist
            playlist = playlists[0]
            for j in range(len(playlist)):
                e2 = playlist[j]
                if e2.text == "Playlist Items":
                    playlist_items = playlist[j+1]
                    playlist_items[:] = playlist_items[:1]  # keep only first playlist item

    return itunes_xml


def add_xml_dict_entry(parent: Element, key: str, value):
    ET.SubElement(parent, "key").text = key

    if isinstance(value, bool):
        # TIL isinstance(True, int) and isinstance(False, int)
        # therefore must check for bool first
        if value:
            ET.SubElement(parent, "true")
        else:
            ET.SubElement(parent, "false")
    elif isinstance(value, int):
        ET.SubElement(parent, "integer").text = str(value)
    elif isinstance(value, str):
        ET.SubElement(parent, "string").text = str(value)
    elif isinstance(value, datetime):
        ET.SubElement(parent, "date").text = value.astimezone(UTC).isoformat().replace('+00:00', 'Z')
    else:
        assert False, value


def convert_to_itunes_xml(lib: Library):
    root = Element("plist", {"version": "1.0"})
    itunes_xml = ElementTree(root)

    root_dict = ET.SubElement(root, "dict")

    # these obviously won't have any correlation with iTunes application versions... so maybe it would be more correct to just hardcode the final values used by the iTunes application?
    add_xml_dict_entry(root_dict, "Major Version", lib.get_int("file_format_major_version"))
    add_xml_dict_entry(root_dict, "Minor Version", lib.get_int("file_format_minor_version"))
    add_xml_dict_entry(root_dict, "Application Version", lib.get_apple_music_version_string())

    add_xml_dict_entry(root_dict, "Date", lib.get_date("date_modified"))

    add_xml_dict_entry(root_dict, "Features", 5)  # not sure what this is... just copied the value out of mine; maybe bit flags for something?
    add_xml_dict_entry(root_dict, "Show Content Ratings", True)  # not stored in Library.musicdb AFAIK, not a big deal to just pick a value

    add_xml_dict_entry(root_dict, "Library Persistent ID", hex(lib.get_int("id_itunes_library")).upper()[2:]) # [2:] to remove 0x prefix

    # todo: tracks and playlists

    add_xml_dict_entry(root_dict, "Music Folder", lib.library_master.get_sub_string("media_folder_uri"))

    return itunes_xml


if __name__ == "__main__":
    # write_itunes_xml(
    #     simplify_itunes_xml("iTunes Music Library example.xml"),
    #     "iTunes Music Library example simplified.xml",
    # )

    lib = Library(
        # path to your library here if the Windows DEFAULT_LIBRARY_FILE is not correct for you
    )
    itunes_xml = convert_to_itunes_xml(lib)
    write_itunes_xml(itunes_xml)
