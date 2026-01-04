""" This script is used to dump a summary of offsets that are not always 0 (i.e. have something to investigate in them). """

import json

from library_musicdb import *

if __name__ == "__main__":
    lib = Library()
    ls = (
        LibrarySearcher()
        .descendants()
    )

    not_zero_offsets = set()

    start = 0
    size = 4
    zeros = b"\x00" * size

    for s in ls.search(lib):
        for i in range(start, len(s._data), size):
            b = s._data[i:i+size]
            if b != zeros:
                not_zero_offsets.add((s.__class__.__name__, i))

    with open("offsets_not_always_zero.txt", "w") as f:
        for cls, offset in sorted(not_zero_offsets):
            print(f"{cls}, {offset}", file=f)
