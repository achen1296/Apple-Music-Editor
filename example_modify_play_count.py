""" This is an example script that shows how you can edit the play count (or any other field) of tracks (or other items like albums, artists, or playlists). """

from library_musicdb import *

if __name__ == "__main__":
    lib = Library(
        # path to your library here if the Windows DEFAULT_LIBRARY_FILE is not correct for you
    )
    ls = (
        LibrarySearcher()
        .descendants_of_type(Track)
        .match_sub_string("name", "word")
    )

    for t in ls.search(lib):
        assert isinstance(t, Track)
        print(t)
        play_count = t.get_sub_int("plays_skips", "play_count")
        t.set_sub_int("plays_skips", "play_count", play_count + 5)

    lib.save()
