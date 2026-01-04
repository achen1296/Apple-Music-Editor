""" This is an example script that shows how you can create playlists from scratch. Specifically, this example:
- uses a regular expression match to filter the tracks
- adds each track to the playlist as many times as its star rating """

from library_musicdb import *

if __name__ == "__main__":
    lib = Library(
        # path to your library here if the Windows DEFAULT_LIBRARY_FILE is not correct for you
    )
    ls = (
        LibrarySearcher()
        .descendants_of_type(Track)
        .re_match_sub_string("artist", r"\bword\b")
    )

    id_and_weight: list[tuple[int, int]] = []

    for t in ls.search(lib):
        assert isinstance(t, Track)
        print(t)
        id_and_weight.append(
            (
                t.get_int("id_track"),
                t.get_int("star_rating") // 20
            )
        )

    playlist_items: list[Section] = []
    for i, w in id_and_weight:
        for _ in range(0, w):
            playlist_items.append(
                bomaPlaylist.from_scratch({
                    "subtype": Playlist.data_subtypes["playlist_item"],
                    "id_track": i,
                })
            )

    lib.playlists.add_child(
        Playlist.from_scratch(
            {
                "name": {
                    "string": "playlist from scratch"
                },
            },
            playlist_items
        )
    )

    lib.save()
