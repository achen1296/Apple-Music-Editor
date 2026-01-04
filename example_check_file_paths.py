""" This is an example script that shows how you can check file paths. """

from pathlib import Path

from library_musicdb import *

if __name__ == "__main__":
    lib = Library(
        # path to your library here if the Windows DEFAULT_LIBRARY_FILE is not correct for you
    )

    all_paths: set[Path] = set()

    for t in lib.tracks.children:
        assert isinstance(t, Track)
        path = Path(t.get_sub_string("file")).resolve()
        all_paths.add(path)
        if not path.exists():
            name = t.get_sub_string("name")
            album = t.get_sub_string("album")
            artist = t.get_sub_string("artist")
            print(f"file of song \"{name}\" (in album \"{album}\" by artist \"{artist}\") is missing:\n{path}")

            # try to fix it? either change the library or move the file if you can figure out where it is
            # for example, I often found that my files went missing because the official program could not decide at what point to truncate album/song names in the file names

    media_folder = Path(lib.library_master.get_sub_string("media_folder_path")).resolve()
    for path, dirs, files in media_folder.walk():
        for f in files:
            if path / f not in all_paths:
                print(f"extra file {path / f}")
