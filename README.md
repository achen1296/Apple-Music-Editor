# Apple Music DB Editor

Editor for Apple Music's Library.musicdb file.

Based on and copying code (see the comments in the code) from:
- https://home.vollink.com/gary/playlister/musicdb.html
- https://github.com/rinsuki/musicdb2sqlite
- https://github.com/jsharkey13/musicdb-to-json

However, unlike these, this project aims not only to read the Library.musicdb file, but also to be able to edit it. How can this be, when large parts of the file format remain a mystery? Simple:
- *start with a known valid file*
- make the desired edits
- change all of the lengths in the headers (which are part of the known format) as needed
- copy back all of the other data exactly as-is

This approach means we cannot *add* whole new entries to arrays, e.g. add a new song. (In the future I might try doing this by copying the mystery data from another entry of the same type.)

# Miscellaneous Observations

- Apple Music appears to use `zlib` compress level 1 (best speed) (experimentally verified by using `load_library` then `save_library` with no edits and seeing which one produces an identical file), but it also seems to accept any compression level (tried saving with different compression levels and opening Apple Music). (Not that there's any particular reason to use another compression level when Apple Music will resave the library itself the next time you open it.)
- On the other hand, it doesn't seem to like it when the size of the encrypted portion is changed — at least none of the sizes I tried was accepted. (Again, not that there's any reason to change this.)