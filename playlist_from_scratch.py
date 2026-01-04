from library_musicdb import *

if __name__ == "__main__":
    lib = Library()

    tracks = lib.tracks
    id_track = None
    for t in tracks.subsections:
        assert isinstance(t, itma)
        id_track = t.get_int("id_track")
        break
    assert id_track is not None

    lib.playlists.add_child(
        Playlist.from_scratch(
            {
                "name": {
                    "string": "playlist from scratch"
                },
            },
            [
                bomaPlaylist.from_scratch({
                    "subtype": Playlist.data_subtypes["playlist_item"],
                    "id_track": id_track,
                })
            ]
        )
    )

    lib.save()
