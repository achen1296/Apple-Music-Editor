from library_musicdb import *

if __name__ == "__main__":
    lib = Library()

    playlists = lib.playlists

    new_playlist = Playlist.from_scratch()
    playlists.add_subsection(new_playlist)

    playlist_name = bomaPlaylist.from_scratch({
        "subtype": 0xC8,
        "string": "playlist from scratch",
        "encoding": StringEncoding.UTF_16_LE
    })
    new_playlist.add_subsection(playlist_name)

    tracks = lib.tracks
    id_track = None
    for t in tracks.subsections:
        assert isinstance(t, itma)
        id_track = t.get_int("id_track")
        break
    assert id_track is not None

    playlist_item = bomaPlaylist.from_scratch({
        "subtype": 0xCE,
        "id_track": id_track,
    })
    new_playlist.add_subsection(playlist_item)

    new_playlist.set_int("tracks_total", 1)

    lib.save()
