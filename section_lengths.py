""" This script is used to dump out the lengths of each section type, counting up how many times each length occurs. This is how I figured out that the section length is consistent except for strings. """

import json

from library_musicdb import *

if __name__ == "__main__":
    lib = Library()
    ls = (
        LibrarySearcher()
        .descendants()
    )

    lengths = {}
    for s in ls.search(lib):

        if s.__class__.__name__ not in lengths:
            lengths[s.__class__.__name__] = {}

        l = len(s._data)
        lengths[s.__class__.__name__][l] = lengths[s.__class__.__name__].get(l, 0) + 1

    # sort descending count
    for cls in lengths:
        lengths[cls] = {
            k: v
            for k, v in sorted(
                lengths[cls].items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }
    with open("section_lengths.json", "w") as f:
        json.dump(lengths, f, indent="\t")
