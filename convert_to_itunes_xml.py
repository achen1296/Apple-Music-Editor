from library_musicdb import *

from xml.etree.ElementTree import ElementTree


def write_itunes_xml(et: ElementTree, file="iTunes Music Library.xml"):
    with open(file, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="UTF-8"?>')
        f.write(b'<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">"')
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


def convert_to_itunes_xml(lib: Library):
    itunes_xml = ElementTree()

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
