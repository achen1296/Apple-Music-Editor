from datetime import UTC, datetime
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import Element, ElementTree

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


def add_xml_dict_key(parent: Element, key: str):
    ET.SubElement(parent, "key").text = key


def add_xml_dict_entry(parent: Element, key: str, value):
    add_xml_dict_key(parent, key)

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

    add_xml_dict_entry(root_dict, "Library Persistent ID", hex(lib.get_int("id_itunes_library")).upper()[2:])  # [2:] to remove 0x prefix

    add_xml_dict_key(root_dict, "Tracks")
    tracks_dict = ET.SubElement(root_dict, "dict")
    for t in lib.tracks.children:
        assert isinstance(t, Track)
        t_id = t.get_int("id_track")
        add_xml_dict_key(tracks_dict, str(t_id))
        t_dict = ET.SubElement(tracks_dict, "dict")

        # iTunes seemed to assign this ID number sequentially and differently upon each export... so repeating what is called the "Persistent ID" below is probably fine since tha tis also unique...
        add_xml_dict_entry(t_dict, "Track ID", t_id)
        add_xml_dict_entry(t_dict, "Size", t.get_sub_int("track_numerics", "file_size"))
        add_xml_dict_entry(t_dict, "Total Time", t.get_sub_int("track_numerics", "track_duration"))
        add_xml_dict_entry(t_dict, "Date Modified", t.get_sub_date("track_numerics", "date_modified"))
        add_xml_dict_entry(t_dict, "Date Added", t.get_sub_date("track_numerics", "date_added"))
        add_xml_dict_entry(t_dict, "Bit Rate", t.get_sub_int("track_numerics", "bit_rate"))
        add_xml_dict_entry(t_dict, "Sample Rate", int(t.get_sub_float("track_numerics", "sample_rate")))
        add_xml_dict_entry(t_dict, "Play Count", t.get_sub_int("plays_skips", "play_count"))
        add_xml_dict_entry(t_dict, "Play Date", t.get_sub_int("plays_skips", "date_last_played"))
        add_xml_dict_entry(t_dict, "Play Date UTC", t.get_sub_date("plays_skips", "date_last_played"))
        add_xml_dict_entry(t_dict, "Skip Count", t.get_sub_int("plays_skips", "skip_count"))
        add_xml_dict_entry(t_dict, "Skip Date", t.get_sub_date("plays_skips", "date_last_skipped"))
        add_xml_dict_entry(t_dict, "Rating", t.get_int("star_rating"))
        # yes, there isn't any Skip Date UTC and Skip Date is in ISO format, not an int timestamp
        add_xml_dict_entry(t_dict, "Loved", t.get_int("suggestion_flag") == SuggestionFlag.LOVE)
        add_xml_dict_entry(t_dict, "Persistent ID", hex(t.get_int("id_track"))[2:].upper())
        # todo is this the correct way to determine this? noted in readme that file type is an offset in track numerics, but not from my own investigation as my own library has 0 for all of them even though an old iTunes XML does not have all tracks as the same file type
        add_xml_dict_entry(t_dict, "Track Type", "File" if t.get_sub_int("track_numerics", "id_apple_music_track") == 0 else "Purchased")
        add_xml_dict_entry(t_dict, "File Folder Count", t.get_sub_int("track_numerics", "file_folder_count"))
        add_xml_dict_entry(t_dict, "Library Folder Count", t.get_sub_int("track_numerics", "library_folder_count"))
        add_xml_dict_entry(t_dict, "Name", t.get_sub_string("name"))
        add_xml_dict_entry(t_dict, "Artist", t.get_sub_string("artist"))
        add_xml_dict_entry(t_dict, "Album Artist", t.get_sub_string("album_artist"))
        add_xml_dict_entry(t_dict, "Composer", t.get_sub_string("composer"))
        add_xml_dict_entry(t_dict, "Album", t.get_sub_string("album"))
        add_xml_dict_entry(t_dict, "Genre", t.get_sub_string("genre"))
        add_xml_dict_entry(t_dict, "Kind", t.get_sub_string("kind"))
        add_xml_dict_entry(t_dict, "Comments", t.get_sub_string("comments"))
        add_xml_dict_entry(t_dict, "Sort Name", t.get_sub_string("sort_name"))
        add_xml_dict_entry(t_dict, "Sort Album", t.get_sub_string("sort_album"))
        add_xml_dict_entry(t_dict, "Sort Artist", t.get_sub_string("sort_artist"))
        add_xml_dict_entry(t_dict, "Location", t.get_sub_string("url"))

        # break # for testing to output only the first one

    add_xml_dict_key(root_dict, "Playlists")
    playlists_array = ET.SubElement(root_dict, "array")
    for p in lib.playlists.children:
        assert isinstance(p, Playlist)
        p_dict = ET.SubElement(playlists_array, "dict")

        if p.get_boolean("is_master"):
            add_xml_dict_entry(p_dict, "Master", True)
        # see the above regarding track IDs - same idea here
        add_xml_dict_entry(p_dict, "Playlist ID", p.get_int("id_playlist"))
        add_xml_dict_entry(p_dict, "Playlist Persistent ID", hex(p.get_int("id_playlist"))[2:].upper())
        # none of my playlists have a different value, not sure what this is...
        add_xml_dict_entry(p_dict, "All Items", True)
        # visible = true for regular playlists
        add_xml_dict_entry(p_dict, "Visible", not p.get_boolean("is_master") and p.get_int("special_playlist") == 0)
        name = p.get_sub_string("name")
        if name == "####!####":  # special case
            name = "Library"
        add_xml_dict_entry(p_dict, "Name", name)

        add_xml_dict_key(p_dict, "Playlist Items")
        i_array = ET.SubElement(p_dict, "array")
        for boma in p.children:
            i = boma.child
            if not isinstance(i, PlaylistItem):
                continue
            # see above regarding track IDs
            i_dict = ET.SubElement(i_array, "dict")
            add_xml_dict_entry(i_dict, "Track ID", i.get_int("id_track"))

            # break # for testing to output only the first one

        # break # for testing to output only the first one

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
