import random

from date_util import datetime_to_int
from library_musicdb import *

if __name__ == "__main__":
    lib = Library()

    playlists = lib.playlists

    new_playlist = Playlist.from_scratch(368, {
        "date_created": datetime_to_int(),
        "id_playlist": random.randrange(0, 1 << (8*8)),
    })
    playlists.add_subsection(new_playlist)

    name_boma = bomaPlaylist.from_scratch(20, {"subtype": 0xC8})
    new_playlist.add_subsection(name_boma)

    name_string = String.from_scratch(16, initial_string="playlist from scratch", encoding="utf_16_le")
    name_boma.add_subsection(name_string)

    ipfa_boma = bomaPlaylist.from_scratch(20, {"subtype": 0xCE})
    new_playlist.add_subsection(ipfa_boma)

    tracks = lib.tracks
    id_track = None
    for t in tracks.subsections:
        assert isinstance(t, itma)
        id_track = t.get_int("id_track")
        break
    assert id_track is not None

    new_ipfa = ipfa.from_scratch(68, {
        "id_ipfa": random.randrange(0, 1 << (8*8)),
        "id_track": id_track,
    })
    ipfa_boma.add_subsection(new_ipfa)
    new_playlist.set_int("tracks_total", 1)

    with open("playlist from scratch.bin", "wb") as f:
        for s in playlists:
            f.write(s.data)

    lib.save()
