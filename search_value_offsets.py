""" This script is used to search for the offsets (relative to the beginning of the sections in which they appear) where different byte values occur. This is useful to find out where values (e.g. an ID) are repeated. """

from library_musicdb import *

if __name__ == "__main__":
    search_for = (
        b"hello"
        # "hello".encode("utf_16_le")
        # pack_int(123, size=2)
        # bytes.fromhex("abcdef")
    )
    search_len = len(search_for)

    lib = Library()
    ls = (
        LibrarySearcher()
        # for example:
        .descendants()
    )

    for i, s in enumerate(ls.search(lib)):
        if search_for in s._data:
            print("-"*32)
            print(s)
            print(s._data)

            index = 0
            l = len(s._data)
            while index < l:
                try:
                    index = s._data.index(search_for, index)
                except ValueError:
                    break
                print(f"found bytes at offset {index}")
                index += search_len  # otherwise will find the same index again
