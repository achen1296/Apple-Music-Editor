from library_musicdb import *

if __name__ == "__main__":
    lib = Library()

    playlists = lib.playlists

    new_playlist = Playlist.from_scratch()
    playlists.add_subsection(new_playlist)

    name_boma = bomaPlaylist.from_scratch({"subtype": 0xC8})
    new_playlist.add_subsection(name_boma)

    name_string = String.from_scratch({
        "string": "playlist from scratch", "encoding": StringEncoding.UTF_16_LE})
    name_boma.add_subsection(name_string)

    ipfa_boma = bomaPlaylist.from_scratch({"subtype": 0xCE})
    new_playlist.add_subsection(ipfa_boma)

    tracks = lib.tracks
    id_track = None
    for t in tracks.subsections:
        assert isinstance(t, itma)
        id_track = t.get_int("id_track")
        break
    assert id_track is not None

    new_ipfa = ipfa.from_scratch({
        "id_track": id_track,
    })
    ipfa_boma.add_subsection(new_ipfa)
    new_playlist.set_int("tracks_total", 1)

    with open("playlist from scratch.bin", "wb") as f:
        for s in playlists:
            f.write(s.data)

    with open("library with playlist from scratch.bin", "wb") as f:
        for s in lib:
            f.write(s.data)

    lib.save()
