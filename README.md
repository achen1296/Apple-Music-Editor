# Apple Music Library.musicdb Editor

Editor for Apple Music's Library.musicdb file.

Based on:

- https://home.vollink.com/gary/playlister/musicdb.html
- https://github.com/rinsuki/musicdb2sqlite
- https://github.com/jsharkey13/musicdb-to-json (also copied a small amount of code from here, see the comments in my code for details)

However, unlike these, this project aims not only to read the Library.musicdb file, but also to be able to edit it. How can this be, when large parts of the file format remain a mystery? Simple:

- _start with a known valid file_
- make the desired edits
- change all of the references (which are hopefully part of the known format) as needed
  - associated section length
  - subsection count
  - some other count, e.g. total song count
  - pointer IDs
- copy back all of the other data exactly as-is

This approach means we cannot _add_ whole new entries to arrays, e.g. add a new song. (In the future I might try doing this by copying the mystery data from another entry of the same type.)

_Note that this code does not support the book subtype of boma sections, because, as mentioned below, my library doesn't have any I could test with, which makes me suspect they are no longer in use anyway._

_In general, I just know it works on my own library file with the types of edits I wanted to do, so I can't give any guarantees about what it does to your library file. For this reason I've made it automatically make backups when you use the program to edit your library, unless you specifically turn them off. They will be called e.g. "Library backup 2026-01-01T00.00.00.musicdb" (if you saved the edited version on midnight of January 1, 2026) and placed in the same folder as Library.musicdb._

So far I have successfully edited simple things like the play count of a track, which does not affect any references. However, I have also made many more discoveries on top of those of the previous people credited above, which makes me hopeful about more complicated edits. Maybe even full understanding of the file!

Take a look at [observations.md](observations.md) for loosely structured notes about what I found during my turn at investigating the format (some of which jsharkey13 found first, as documented by their code, and which I independently confirmed without realizing initially). I kept it for archival/documentation purposes. For the clean version, I have combined them with the information from other people into the below: what I believe is the most complete public Library.musicdb format description! Eventually I will send this to Gary Vollink, so if his site includes all of the new information, it came from me.

> "If I have seen further, it is by standing on the shoulders of giants."

-Isaac Newton

# Table of Contents

- [General Notes](#general-notes)
- [Section Structure](#section-structure)

---

- [hfma (File Header)](#hfma-file-header)
- [hsma (Section Header)](#hsma-section-header)

---

- [boma (Binary Object)](#boma-binary-object)
- [String Section](#string-section)
- [Raw String](#raw-string)

---

- [plma (Library Master)](#plma-library-master)

---

- [lama (Album List)](#lama-album-list)
- [iama (Album)](#iama-album)

---

- [lAma (Artist List)](#lama-artist-list)
- [iAma (Artist)](#iama-artist)

---

- [ltma (Track List)](#ltma-track-list)
- [itma (Track)](#itma-track)
- [Track Numerics](#track-numerics)
- [Track Plays and Skips](#track-plays-and-skips)
- [Video](#video)

---

- [lPma (Playlist List)](#lpma-playlist-list)
- [lpma (Playlist)](#lpma-playlist)
- [ipfa (Playlist Item)](#ipfa-playlist-item)
- [Smart Playlist Options](#smart-playlist-options)
- [SLst (Smart Playlist Rules)](#slst-smart-playlist-rules)
- [Text Match Rule](#text-match-rule)

---

- [LPma (Padding?)](#lpma-padding)

---

- [Accompanying Files](#relevant-accompanying-files)
- [Data Stored in the Audio File](#data-stored-in-the-audio-file)

# General Notes

[Back to TOC](#table-of-contents)

- For the details on encryption/compression, see his site, or just look at the functions `load_library_bytes` and `save_library_bytes`. The documentation below is after this process to recover the "raw" bytes.
- I will also assume little-endianness because nobody has documented a case of big-endianness, even though Gary Vollink speculates it might be possible. Therefore 0x 04 03 02 01 interpreted as an unsigned int is 16909060, not 67305985.
  - UTF-16 strings are always little-endian.
- Integers are almost always unsigned, it will be noted where this is not the case.
- Booleans (checkboxes) are always 1 byte, 0 = false, 1 = true.
- In the tables below, an offset "..." means all of the offsets in between the previous and next entries (or until the end of the section if at the end) were always 0 in my library (unless I missed any).
  - It is tempting to assume that these are just reserved empty space — but this is not always the case! There are many cases where 0 is the default value indicating that some feature is not used, a pointer is not assigned, etc., and your library file will always contain 0 there if you happen to have never used that feature!
- While I was dissecting the meaning of each part of the file I found that:
  - a value with sparse bits like 0x 03 01 00 01 is usually a collection of bit or enum flags
  - a low value like 25, 304, etc. is usually some kind of count
    - a value that has several ff bytes at the end is likely a negative value of low magnitude represented as a signed integer
  - a value with dense bits like 0x cd 3a 45 18 is usually some kind of ID
  - with one exception to the previous: dates are expressed in seconds since 1904-01-01T00:00 (former MacOS epoch), therefore values in the high 3 billions (or higher if you are reading this in the 2030s and beyond) should be suspected as dates
  - try throwing numbers (in decimal) into a search "site:music.apple.com \<number\>" if you think it might be a store ID
- "(a?)" is shorthand for "(always?)", speculating that an offset always has the value given in the example because it is the only one I have ever seen (not having this doesn't mean an offset has multiple observed values — I may have just missed it).
  - In principle, section lengths could be different between sections of the same type. In practice, however, they are always the same for a certain section type, with the exception of the badly-behaved [boma](#boma-binary-object) (nice alliteration ;) children. Therefore I will not mark these with (a?) and you may assume the example value is the one and only value that ever appears.

# Section Structure

[Back to TOC](#table-of-contents)

The file is divided into what most have previously called "sections". Sections may have subsections, creating a tree structure (so I also call them "children"). If section A has subsections B and C, and B has subsections D and E, then they will appear in the file in the order A B D E C

Almost all sections begin with 8 bytes that have the same meaning.

| Offset | Length | Meaning                | Examples Value(s) |
| ------ | ------ | ---------------------- | ----------------- |
| 0      | 4      | Section signature      | hfma, hsma, etc.  |
| 4      | 4      | Section length (bytes) | 20                |

These are also extremely common, but not universal.

| Offset  | Length | Meaning                                                                               | Examples Value(s) |
| ------- | ------ | ------------------------------------------------------------------------------------- | ----------------- |
| 8       | 4      | Associated sections length (bytes) - length of this section + all subsections (bytes) | 1234              |
| 8 or 12 | 4      | Number of subsections                                                                 | 3                 |
| 12      | 4      | Section subtype (enum value that hints at the subsection contents)                    | 3                 |

Using either associated sections length (which I call "total size" in some places in my code") or number of subsections, it is possible to determine where the subsections end and the next section at either the same level or a higher one begins (a section with subsections usually must have at least one of these). Some kinds of sections have both of these, which is why number of subsections is occasionally at offset 12 instead of 8. When this is the case, my code prefers to use the associated sections length, because it is possible to use this to continue on afterward even in the case of mysterious subsections.

# hfma (File Header)

[Back to TOC](#table-of-contents)

Seems completely understood: X

Speculation: "Apple Music file header" (acronym reversed due to endianness)? Or maybe "header (of) file, media (data type)" or "header (of) file master"?

There is one version of this section outside of the encryption/compression process, containing the metadata needed to reverse it. There is also a version of this section inside, which is _mostly_ a copy of the outer one where it has non-zero values. Maybe it's used to verify correct decryption/decompression.

| Offset | Length | Meaning                                                                                                                        | Examples Value(s)                               | Duplicated in Inner Copy  |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------- | ------------------------- |
| 0      | 4      | Section signature                                                                                                              | hfma                                            | -                         |
| 4      | 4      | Section length (bytes)                                                                                                         | 160                                             | -                         |
| 8      | 4      | File length in bytes (when encrypted/compressed, not raw, therefore this cannot be considered as "associated sections length") | 5767                                            | no (0 in inner)           |
| 12     | 2      | File format major version                                                                                                      | 21                                              | yes                       |
| 14     | 2      | File format minor version                                                                                                      | 1                                               | yes                       |
| 16     | 32     | Apple Music version as null-terminated string                                                                                  | 1.0.1.37                                        | yes                       |
| 48     | 8      | Library ID                                                                                                                     | 0xF60BBBD97C7D8F41                              | yes                       |
| 56     | 4      | musicdb file type                                                                                                              | see below                                       | no                        |
| 60     | 4      | ?                                                                                                                              | 20 (a?)                                         | yes                       |
| 64     | 4      | ? (not zero but different between inner and outer, might be bit flags)                                                         | 0x 02 01 01 00 (outer) / 0x 02 00 00 00 (inner) | different (both non-zero) |
| 68     | 4      | Song count                                                                                                                     | 136                                             | no                        |
| 72     | 4      | Playlist count                                                                                                                 | 15                                              | no                        |
| 76     | 4      | ?                                                                                                                              | 0x CB 01 00 00                                  | no                        |
| 80     | 4      | Artist count                                                                                                                   | 24                                              | no                        |
| 84     | 4      | Max crypt size                                                                                                                 | 102400 (a?)                                     | no                        |
| 88     | 4      | Library time offset in seconds (i.e. timezone)                                                                                 | -14400 (US/NY) (_signed value_)                 | yes                       |
| 92     | 8      | Your Apple Store account ID (0 when not signed in)                                                                             | 0xA10D876FF3940021                              | yes                       |
| 100    | 4      | Library modification date                                                                                                      | 3658272271                                      | yes                       |
| 104    | 4      | ?                                                                                                                              | 1 (outer) / 0 (inner)                           | different                 |
| 108    | 8      | Library ID (if from iTunes import)                                                                                             | repeat of offset 48, or 0                       | yes                       |
| 116    | 4      | ?                                                                                                                              | 0x 23 01 00 00 (outer) / 0 (inner)              | different                 |
| 120    | 8      | an ID? (not repeated anywhere else in file)                                                                                    | 0x 3F F2 06 1B 6E 62 23 1E                      | yes                       |
| ...    |        | 0s?                                                                                                                            |

Offset 56 musicdb file type enum values:

- 6 = Library.musicdb
- 5 = Application.musicdb (in Big Sur)
- 4 = Application.musicdb (in Catalina)
- 2 = Library Preferences.musicdb
- 7 = also Library.musicdb (this is the value my library has)

Parents: none (outer) / [hsma](#hsma-section-header) (inner)

Children: [hsma](#hsma-section-header) (outer) / none (inner)

# hsma (Section Header)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music section header"?

| Offset | Length | Meaning                    | Examples Value(s) |
| ------ | ------ | -------------------------- | ----------------- |
| 0      | 4      | Section signature          | hsma              |
| 4      | 4      | Section length             | 56                |
| 8      | 4      | Associated sections length | 1234              |
| 12     | 4      | Section subtype            | 3                 |
| ...    |        | 0s                         |

Parents: [hfma](#hfma-file-header) (outer)

Children, depends on the subtype (presented in the order they seem to always appear in the file):

- 3 = [hfma](#hfma-file-header) (inner)
- 6 = [plma](#plma-library-master)
- 4 = [lama](#lama-album-list)
- 5 = [lAma](#lama-artist-list)
- 1 = [ltma](#ltma-track-list)
- 2 = [lPma](#lpma-playlist-list)
- 17 = [LPma (Padding?)](#lpma-padding)

# boma (Binary Object)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music object binary"?

| Offset | Length | Meaning                    | Examples Value(s) |
| ------ | ------ | -------------------------- | ----------------- |
| 0      | 4      | Section signature          | hsma              |
| 4      | 4      | Section length             | 20                |
| 8      | 4      | Associated sections length | 160               |
| 12     | 4      | Section subtype            | 3                 |
| 16     | 4      | 0s                         | 0 (a?)            |

Here is a major disagreement with Gary Vollink's table: he, and therefore everyone after him but before me, believed that boma sections broke the usual pattern, and thought boma sections had at offset 4 a mysterious value "Depends, always 0x14", while the section length was at offset 8 instead of at 4 as usual. But I believe that boma sections are _not_ the ones that break the pattern. The realization for me came from looking at [smart playlist rules](#slst-smart-playlist-rules), which clearly had a section header "SLst" the repeated once for each rule, along with noticing that Gary Vollink came so close to the same realization with boma sections of subtype 0xce, containing [ipfa](#ipfa-playlist-item) subsections — in that case, he labeled offset 4 "subdata start" but still called offset 8 the section length. The problem is that _the children_ of boma sections break the pattern — many do not have a signature, at least not one made of printable ASCII characters, and offset 4 is never(?) the section length. This is why I speculate that the "bo" means "object binary"/"binary object", as an indication that the children do not follow the usual section-based format, even though obviously everything is in binary.

For children of boma, this means that all offsets listed on Gary Vollink's page or in jsharkey13's code will be 20 greater than the ones I am listing.

From a practical point of view this doesn't change that much because you will often still need the associated sections length to make sure to read the correct amount of subsection data, and the subtype to know how to interpret it, but at least it explains the "always 0x14", and makes the pattern break less strange in that it is complete, dramatic, and more obviously intentional rather than seemingly very subtle for no good reason.

Parents:

- [plma](#plma-library-master)
- [iama](#iama-album)
- [iAma](#iama-artist)
- [lpma](#lpma-playlist)

Children: Depends on subtype. See each of the parents, which list their grandchildren. But common ones include:

- [String Section](#string-section)
- [Raw String](#raw-string)
- Book (See Gary Vollink's page for a description. I don't have any in my Library.musicdb file, so I couldn't test anything on them and I didn't write any code for them. However, some boma subtypes that Gary Vollink lists as having book data inside have the normal string format instead in my library, so I suspect they are no longer in use, which makes sense because they seem unnecessarily long and complicated.)

# String Section

[Back to TOC](#table-of-contents)

Seems completely understood: X

| Offset | Length   | Meaning                                                                       | Examples Value(s) |
| ------ | -------- | ----------------------------------------------------------------------------- | ----------------- |
| 0      | 4        | Section signature, 2 for UTF-16 and 1 for UTF-8                               | 1, 2              |
| 4      | 4 (8?)   | _String_ length, _not_ section length — only measured starting from offset 16 | 100               |
| ...    |          | ?                                                                             |
| 16     | variable | The string data in the specified encoding                                     | any string        |

Parents: [boma](#boma-binary-object), many different subtypes

# Raw String

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

These are in UTF-8 or UTF-16. It is not clear why some strings are inside of sections, and some are just given raw. The only surefire way to infer that data is a raw string and which encoding it is in is the parent boma sections's subtype, and the only surefire way to infer the string's length is the parent boma section's associated section length.

| Offset | Length   | Meaning     | Examples Value(s)            |
| ------ | -------- | ----------- | ---------------------------- |
| 0      | variable | string data | "\<?xml=...", "C:/Users/..." |

Parents: [boma](#boma-binary-object), many different subtypes

# plma (Library Master)

[Back to TOC](#table-of-contents)

Seems completely understood: X

"Apple Music library playlist"? (I believe the entire library used to be encoded as a special kind of playlist in iTunes.)

| Offset | Length | Meaning                                                                                                                 | Examples Value(s)  |
| ------ | ------ | ----------------------------------------------------------------------------------------------------------------------- | ------------------ |
| 0      | 4      | Section signature                                                                                                       | plma               |
| 4      | 4      | Section length                                                                                                          | 194                |
| 8      | 4      | Number of subsections                                                                                                   | 6                  |
| ...    |        | ?                                                                                                                       |
| 52     | 4      | ? (0x 00 00 02 00 in my library)                                                                                        |
| 58     | 8      | Library ID                                                                                                              | 0xF60BBBD97C7D8F41 |
| ...    |        | ?                                                                                                                       |
| 68     | 4      | ? (0x 00 00 08 00 in my library)                                                                                        |
| ...    |        | ?                                                                                                                       |
| 92     | 8      | Library ID (again)                                                                                                      | 0xF60BBBD97C7D8F41 |
| ...    |        | ?                                                                                                                       |
| 104    | 4      | ? (found repeated at offset 244 of [itma](#itma-track), inside [track numerics](#track-numerics) at offset 200 and 280) | 0x 78 A0 72 78     |
| ...    |        | ?                                                                                                                       |
| 128    | 4      | ? (2 in mine)                                                                                                           |
| ...    |        | ?                                                                                                                       |
| 136    | 4      | ? (256 in mine)                                                                                                         |
| ...    |        | ?                                                                                                                       |
| 144    | 4      | ? (0x 00 00 01 01 in mine)                                                                                              |
| 148    | 4      | ? (1 in mine)                                                                                                           |
| ...    |        | ?                                                                                                                       |
| 160    | 4      | ? (0x 00 00 02 00 in mine)                                                                                              |
| ...    |        | ?                                                                                                                       |
| 168    | 4      | ? (0x 00 00 01 00 in mine)                                                                                              |
| ...    |        | ?                                                                                                                       |
| 176    | 4      | ? (0x 00 00 08 00 in mine)                                                                                              |
| ...    |        | ?                                                                                                                       |

Parents: [hsma](#hsma-section-header)

Children: [boma](#boma-binary-object)

Grandchildren:

- [Strings](#string-section):
  - boma subtype 0x1F8 = media folder URI
- [Raw Strings](#raw-string)
  - 0x1FC = imported iTunes .itl file
  - 0x1FD = media folder path (_encoded as UTF-16_)
  - 0x200 = exactly the same as 0x1FD
- Unknown:
  - 0x1F6 (contains an ID? not repeated anywhere)
  - 0x1FF (contains 2 copies of library ID in my library)

# lama (Album List)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music album list"?

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Section signature     | lama              |
| 4      | 4      | Section length        | 48                |
| 8      | 4      | Number of subsections | 1234              |
| ...    |        | 0s                    |

Parents: [hsma](#hsma-section-header)

Children: [iama](#iama-album)

# iama (Album)

[Back to TOC](#table-of-contents)

Seems completely understood: X

"Apple Music album item"?

| Offset | Length | Meaning                                                                                                                                                | Examples Value(s)   |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------- |
| 0      | 4      | Section signature                                                                                                                                      | iama                |
| 4      | 4      | Section length                                                                                                                                         | 140                 |
| 8      | 4      | Associated sections length                                                                                                                             | 1234                |
| 12     | 4      | Number of subsections                                                                                                                                  | 2                   |
| 16     | 8      | Album ID                                                                                                                                               | 0x9356DCFEC6CB1913  |
| 24     | 4      | ? (usually 0x 02 00 00 01, sometimes 0x 02 01 00 01)                                                                                                   |                     |
| 28     | 4      | ?                                                                                                                                                      | 1 (a?)              |
| 32     | 8      | Track ID of first track in album, but sometimes 0 (is it possible to have an empty album?)                                                             | 0xC89ECA05FB184E3E  |
| 40     | 1      | Star rating (1 star = 20, 5 stars = 100)                                                                                                               | 20                  |
| 41     | 1      | ? (during experimentation, 0x20 for 0 stars, 0x01 for all other ratings; but file also contains these 2 values in other combinations with ratings)     |
| 42     | 1      | Suggestion flag                                                                                                                                        | see below           |
| ...    |        | ?                                                                                                                                                      |
| 64     | 8      | Album ID again, but sometimes 0 (usually for newer albums? iTunes ID?)                                                                                 | repeat of offset 16 |
| ...    |        | ?                                                                                                                                                      |
| 96     | 4      | Suggestion flag modified date                                                                                                                          |
| 100    | 4      | Last played (most recent last played date of any track in the album, 0 if all never played)                                                            | 3818534400          |
| 104    | 4      | Album ID in Apple Music store - plug into the end of the URL "https://music.apple.com/album/..." as decimal - 0 if a custom album                      |                     |
| ...    |        | ?                                                                                                                                                      |
| 120    | 4      | ? (nearly always 2, but rarely otherwise found duplicated at offset 120 of [iAma (Artist)](#iama-artist) and nowhere else, might be a date when not 2) |                     |
| ...    |        | ?                                                                                                                                                      |

Offset 42 suggestion flag enum values: see [itma](#itma-track)

Parents: [lama](#lama-album-list)

Children: [boma](#boma-binary-object)

Grandchildren:

- [Strings](#string-section):
  - 0x12C = album name
  - 0x12D = artist name
  - 0x12E = album artist name

# lAma (Artist List)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music artist list"?

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Section signature     | lAma              |
| 4      | 4      | Section length        | 100               |
| 8      | 4      | Number of subsections | 3                 |
| ...    |        | 0s                    |

Parents: [hsma](#hsma-section-header)

Children: [iAma](#iama-artist)

# iAma (Artist)

[Back to TOC](#table-of-contents)

Seems completely understood: X

"Apple Music artist item"?

| Offset | Length | Meaning                                                                                                                                                        | Examples Value(s)                      |
| ------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| 0      | 4      | Section signature                                                                                                                                              | iAma                                   |
| 4      | 4      | Section length                                                                                                                                                 | 132                                    |
| 8      | 4      | Associated sections length                                                                                                                                     | 1234                                   |
| 12     | 4      | Number of subsections                                                                                                                                          | 5                                      |
| 16     | 8      | Artist ID (local)                                                                                                                                              | 0xAAE367957FF01CEC                     |
| 24     | 4      | ?                                                                                                                                                              | 2 (a?)                                 |
| 28     | 4      | ?                                                                                                                                                              | 1 (a?)                                 |
| ...    |        | ?                                                                                                                                                              |
| 52     | 4      | Artist ID in Apple Music store - plug into the end of the URL "https://music.apple.com/artist/..." as decimal - 0 if a custom artist                           | 461932 ("It's the Final Countdown...") |
| ...    |        | ?                                                                                                                                                              |
| 64     | 16     | Artwork UUID in [artwork.sqlite](#artworksqlite), only for remote images, see that section for details                                                         | 0xDDAE1C...                            |
| 80     | 8      | Artist ID again, but sometimes 0 (iTunes?)                                                                                                                     | repeat of 16                           |
| ...    |        | ?                                                                                                                                                              |
| 96     | 4      | ? (almost always 0 but sometimes 45)                                                                                                                           |
| 100    | 4      | ? (almost always 0x 00 00 00 01 but sometimes 0x 05 00 00 01)                                                                                                  |
| 104    | 4      | ? (almost always 0 but sometimes 1)                                                                                                                            |
| ...    |        | ?                                                                                                                                                              |
| 120    | 4      | ? (almost always 2, but rarely otherwise see [iama](#iama-album) offset 120, the set of values found here are a superset of those, might be a date when not 2) |
| ...    |        | ?                                                                                                                                                              |

Parents: [lAma](#lama-artist-list)

Children: [boma](#boma-binary-object)

Grandchildren:

- [Strings](#string-section):
  - 0x190 = artist name
  - 0x191 = sort name
- [Raw Strings](#raw-string)
  - 0x192 = artwork URL plist (XML)

# ltma (Track List)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music track list"?

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Section signature     | ltma              |
| 4      | 4      | Section length        | 92                |
| 8      | 4      | Number of subsections | 3                 |
| ...    |        | 0s                    |

Parents: [hsma](#hsma-section-header)

Children: [itma](#itma-track)

# itma (Track)

[Back to TOC](#table-of-contents)

Seems completely understood: X

"Apple Music track item"?

| Offset  | Length  | Meaning                                                                                                                                                                                                                                 | Examples Value(s)                        |
| ------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| 0       | 4       | Section signature                                                                                                                                                                                                                       | itma                                     |
| 4       | 4       | Section length                                                                                                                                                                                                                          | 376                                      |
| 8       | 4       | ? (usually in range 1000-3000, observed changing when equalizer is set)                                                                                                                                                                 | 0x F3 0C 00 00                           |
| 12      | 4       | Number of subsections                                                                                                                                                                                                                   | 18                                       |
| 16      | 8       | Track ID                                                                                                                                                                                                                                | 0xD5F6F65777A704BC                       |
| 24      | 4       | ? (counts up by 2 starting from 1002 in the order the tracks appear in the file)                                                                                                                                                        | 1002                                     |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 30      | 1       | Checkbox "Skip when shuffling"                                                                                                                                                                                                          | 0 or 1                                   |
| 31      | 1       | ? (usually 1, but sometimes 0, looks like another boolean)                                                                                                                                                                              |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 33      | 1       | ? (usually 0, but sometimes 1, looks like another boolean)                                                                                                                                                                              |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 35      | 1       | ? (always 1, looks like another boolean given the context)                                                                                                                                                                              |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 38      | 1       | Checkbox "Album is compilation"                                                                                                                                                                                                         |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 42      | 1       | Disabled (boolean) (this is what jsharkey13 labels it as but I'm not sure what this means)                                                                                                                                              |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 47      | 1       | ? (almost always 0, rarely 1, likely another boolean)                                                                                                                                                                                   |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 50      | 1       | Checkbox "Remember playback position"                                                                                                                                                                                                   |
| 51      | 1       | Checkbox "Show composer in all views"                                                                                                                                                                                                   |
| 52      | 1       | Checkbox "Use work & movement", keeps associated information even if unchecked (only affects display)                                                                                                                                   |
| 53      | 1       | ? (almost always 0, sometimes 1, likely another boolean)                                                                                                                                                                                |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 55      | 1       | ? (usually 1, sometimes 0, likely another boolean)                                                                                                                                                                                      |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 57      | 1       | ? (always 1, likely another boolean)                                                                                                                                                                                                    |
| 58      | 1       | Purchased (boolean)                                                                                                                                                                                                                     |
| 59      | 1       | Content rating                                                                                                                                                                                                                          | see below                                |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 62      | 1       | Suggestion flag                                                                                                                                                                                                                         | see below                                |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 64      | 1       | ? (almost always 0, sometimes 1, likely another boolean)                                                                                                                                                                                |
| 65      | 1       | Star rating (1 star = 20, 5 stars = 100)                                                                                                                                                                                                | 20                                       |
| 66-72   | 1 each? | ? (see example values)                                                                                                                                                                                                                  | 0x80, 0x81, 0x1, 0x3                     |
| 82      | 2       | Beats per minute                                                                                                                                                                                                                        | 144                                      |
| 84      | 2       | Disc number of this track                                                                                                                                                                                                               | 1                                        |
| 86      | 2       | Total movements (denominator for offset 88)                                                                                                                                                                                             | 5                                        |
| 88      | 2       | Movement number of this track                                                                                                                                                                                                           | 3                                        |
| 90      | 2       | Total discs (denominator for offset 84)                                                                                                                                                                                                 | 3                                        |
| 92      | 4       | ? (almost always 0, but otherwise looks like a small signed value)                                                                                                                                                                      | 0, 255, -1, 136, 75, -128, 153, 89, -230 |
| 96      | 4       | ? (not 0 only for purchased tracks, when not 0 looks like an ID, however not unique, can be shared between itma's in the same album, but not repeated elsewhere)                                                                        |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 108     | 4?      | ? (always 1 in my library)                                                                                                                                                                                                              |
| 112     | 4?      | ? (always 1 in my library)                                                                                                                                                                                                              |
| 116     | 2       | Total tracks (denominator for offset 160)                                                                                                                                                                                               | 3                                        |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 148     | 4       | Playback start position in milliseconds (0 for not set)                                                                                                                                                                                 | 1100                                     |
| 152     | 4       | Playback stop position in ms (0 for not set)                                                                                                                                                                                            | 5000                                     |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 160     | 2       | Track number                                                                                                                                                                                                                            | 2                                        |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 168     | 4       | Track year                                                                                                                                                                                                                              | 2015                                     |
| 172     | 8       | Album ID                                                                                                                                                                                                                                |
| 180     | 8       | Artist ID (see [iAma](#iama-artist) offset 16)                                                                                                                                                                                          |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 220     | 8       | ? (not 0 only for songs purchased from Apple Music, repeated at 300 of the same section, 328 of a [track numerics](#track-numerics), values for tracks in the same album are close together and often consecutive, might be another ID) |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 244     | 4       | ? (see [plma](#plma-library-master) offset 104)                                                                                                                                                                                         |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 252     | 4       | ? (0x 00 00 03 00 for purchased songs, otherwise 0)                                                                                                                                                                                     |
| 256     | 16      | Artwork UUID in [artwork.sqlite](#artworksqlite), whichever is the "default" (since you can attach multiple), 0 if none                                                                                                                 | 0xDDAE1C...                              |
| 272     | 8       | Track ID again sometimes (why?)                                                                                                                                                                                                         |
| 280     | 4       | ? (always the same value for tracks with the same title, no matter what album, tiny hash of the title? last byte always 0)                                                                                                              |
| 284-308 | 4 each  | ? (always a multiple of 1000, many unrelated tracks share the same value — maybe an attribute of the audio format?)                                                                                                                     |
| 308     | 4       | ? (always 6, 0, 11, 17, in descending order of frequency)                                                                                                                                                                               |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 320     | 8       | ? (see offset 220)                                                                                                                                                                                                                      |
| 328     | 4       | ? (almost always 3, otherwise 5)                                                                                                                                                                                                        |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 336     | 4       | Suggestion flag modified date, 0 if never                                                                                                                                                                                               |
| ...     |         | ?                                                                                                                                                                                                                                       |
| 344     | 4       | ? (always 0 or 1)                                                                                                                                                                                                                       |
| 348     | 4       | ? (always 0, 1, or 2)                                                                                                                                                                                                                   |
| 352     | 4       | Date added of the most recently added track, only on that track, otherwise 0                                                                                                                                                            |
| ...     |         | ?                                                                                                                                                                                                                                       |

Offset 59 content rating enum values:

- 0 = default
- 1 = explicit
- 2 = clean
- 4 = parental guidance? (jsharkey13 is not sure, and I do not have any data with this flag set)

Offset 62 suggestion flag enum values:

- 0 = default
- 2 = favorite
- 3 = suggest less
- 1 = removed favorite/suggest less (not sure why this doesn't just revert to 0)

Parents: [ltma](#ltma-track-list)

Children: [boma](#boma-binary-object)

Grandchildren:

- 0x1: [track numerics](#track-numerics)
- 0x17: [track plays and skips](#track-plays-and-skips)
- 0x24: [video](#video)
- [Strings](#string-section):
  - 0x2 = title
  - 0x3 = album
  - 0x4 = artist
  - 0x5 = genre
  - 0x6 = kind - e.g. "MPEG audio file"
  - 0x7 = equalizer - always a UTF-16 string that looks like "#!#\<number\>#!#" where the number is different for each equalizer option, strange that this is not a single-byte enum
  - 0x8 = comment
  - 0xB = URL - for local files, URL-encoded version of the file path "file:///C:/Users..."
  - 0xC = composer
  - 0xE = grouping
  - 0x12 = episode description
  - 0x16 = episode synopsis
  - 0x18 = series title
  - 0x19 = episode number
  - 0x1B = album artist
  - 0x1C = content rating
  - 0x1D = asset info plist (XML)
  - 0x1E = title sort
  - 0x1F = album sort
  - 0x20 = artist sort
  - 0x21 = album artist sort
  - 0x22 = composer sort
  - 0x2B = [isrc](https://en.wikipedia.org/wiki/International_Standard_Recording_Code)
  - 0x2E = copyright
  - 0x33 = series synopsis
  - 0x34 = flavor string
  - 0x3B = purchaser username
  - 0x3C = purchaser name
  - 0x3F = work name
  - 0x40 = movement name
  - 0x43 = file path
  - 0x12F = series title
- [Raw Strings](#raw-string)
  - 0x36 = artwork plist (XML)
  - 0x38 = redownload parameters plist (XML)

# Track Numerics

[Back to TOC](#table-of-contents)

Seems completely understood: X

The length is always 364 bytes (the boma parent always has associated sections length 384).

| Offset | Length | Meaning                                                                                                                         | Examples Value(s)                    |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| 0      | 4      | ? (a counter value incrementing by 2 from 1003)                                                                                 | 1003                                 |
| ...    |        | ?                                                                                                                               |
| 8      | 8      | ? (an ID? doesn't appear elsewhere)                                                                                             |
| ...    |        | ?                                                                                                                               |
| 60     | 4      | Sample rate in Hz (float32)                                                                                                     | 44100.0 (0x 00 44 2C 47 20 33 50 4D) |
| ...    |        | ?                                                                                                                               |
| 72     | 2      | File folder count                                                                                                               |
| 74     | 2      | Library folder count                                                                                                            |
| 76     | 2      | Number of artworks (you can attach more than one)                                                                               |
| ...    |        | ?                                                                                                                               |
| ...    |        | ?                                                                                                                               |
| 84     | 4      | Total size of all attached artworks (bytes)                                                                                     | 234                                  |
| 88     | 4      | Bit rate                                                                                                                        |
| ...    |        | ?                                                                                                                               |
| 112    | 4      | Date added                                                                                                                      |
| ...    |        | ?                                                                                                                               |
| 124    | 4      | Custom lyrics tiny hash? (0 if no custom lyrics, otherwise, always the same value for the same custom lyrics)                   |
| 128    | 4      | Date added                                                                                                                      |
| 132    | 4      | Normalization                                                                                                                   |
| 136    | 4      | Purchase date                                                                                                                   |
| 140    | 4      | Release date                                                                                                                    |
| ...    |        | ?                                                                                                                               |
| 156    | 4      | Song duration in milliseconds                                                                                                   |
| 160    | 4      | Album ID in Apple Music store (see [iama](#iama-album) offset 104)                                                              |
| ...    |        | ?                                                                                                                               |
| 168    | 4      | Artist ID in Apple Music store (see [iAma](#iama-artist) offset 52)                                                             |
| ...    |        | ?                                                                                                                               |
| 200    | 4      | ? (see [plma](#plma-library-master) offset 104)                                                                                 |
| ...    |        | ?                                                                                                                               |
| 208    | 4      | _Album_ Artist ID in Apple Music store (see [iAma](#iama-artist) offset 52)                                                     |
| ...    |        | ?                                                                                                                               |
| 280    | 4      | ? (see [plma](#plma-library-master) offset 104)                                                                                 |
| ...    |        | ?                                                                                                                               |
| 296    | 4      | File size                                                                                                                       |
| ...    |        | ?                                                                                                                               |
| 304    | 4      | Song ID in Apple Music store - plug into the end of the URL "https://music.apple.com/song/..." as decimal - 0 if a custom album |
| ...    |        | ?                                                                                                                               |
| 328    | 8      | ? (see [itma](#itma-track) offset 220)                                                                                          |
| ...    |        | ?                                                                                                                               |

Grandparents: [itma](#itma-track)

Parents: [boma](#boma-binary-object) (subtype 0x1)

# Track Plays and Skips

[Back to TOC](#table-of-contents)

Seems completely understood: X

The length is always 52 bytes (the boma parent always has associated sections length 72).

| Offset | Length | Meaning           | Examples Value(s) |
| ------ | ------ | ----------------- | ----------------- |
| 0      | 8      | Track ID          |
| 8      | 4      | Last played date  |
| 12     | 4      | Play count        |
| ...    |        | ?                 |
| 28     | 4      | Last skipped date |
| 32     | 4      | Skip count        |
| ...    |        | ?                 |

Grandparents: [itma](#itma-track)

Parents: [boma](#boma-binary-object) (subtype 0x17)

# Video

[Back to TOC](#table-of-contents)

Seems completely understood: X

The length is always...? (I don't have any of these in my library to check.)

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Vertical resolution   | 480               |
| 4      | 4      | Horizontal resolution | 640               |
| ...    |        | ?                     |
| 68     | 4      | Framerate?            | 24                |
| ...    |        | ?                     |

Grandparents: [itma](#itma-track)

Parents: [boma](#boma-binary-object) (subtype 0x24)

# lPma (Playlist List)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music playlist list"?

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Section signature     | lPma              |
| 4      | 4      | Section length        | 92                |
| 8      | 4      | Number of subsections | 8                 |
| ...    |        | 0s                    |

Parents: [hsma](#hsma-section-header)

Children: [lpma](#lpma-playlist)

# lpma (Playlist)

[Back to TOC](#table-of-contents)

Seems completely understood: X

"Apple Music playlist"?

One always gets a number of lpma entries for special built-in playlists. They do not appear in the GUI under the list of playlists with the ones you created. They are named:

- "####!####" (contains an entry for every track, might be the "Songs" list)
- "Music"
- "Music Videos"
- "TV & Movies"
- "Downloaded" (songs purchased from Apple Music that are downloaded locally)

Playlist folders are implemented as special playlists, along with the parent folder pointer ID at offset 50. Therefore, they do not get their own section type. Even more specifically, they are special kinds of smart playlists. In fact, their binary data are nearly identical to smart playlists (including subsection data) with rules that look like:

- Match _any_ of the following rules:
  - Playlist is \<1st playlist in folder\>
  - Playlist is \<2nd playlist in folder\>
  - etc.

See [SLst (Smart Playlist Rules)](#slst-smart-playlist-rules) for more on this.

| Offset | Length | Meaning                                                                                                                      | Examples Value(s)  |
| ------ | ------ | ---------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| 0      | 4      | Section signature                                                                                                            | lpma               |
| 4      | 4      | Section length                                                                                                               | 368                |
| 8      | 4      | Associated sections length                                                                                                   | 1234               |
| 12     | 4      | Number of subsections                                                                                                        | 8                  |
| 16     | 4      | Number of tracks in playlist                                                                                                 | 10                 |
| ...    |        | ?                                                                                                                            |
| 22     | 4      | Playlist creation date                                                                                                       | 3818534400         |
| 26     | 1? 2?  | ? (observed changing when artwork and/or suggestion flag are changed for the first time)                                     |
| 28     | 2?     | ? (always 0-3)                                                                                                               |
| 30     | 8      | Playlist ID                                                                                                                  | 0x883E9012A290710E |
| 38     | 1? 4?  | ? (always 1)                                                                                                                 | 0x883E9012A290710E |
| ...    |        | ?                                                                                                                            |
| 44     | 1? 2?  | ? (always 0 except for the "####!####" playlist, which has 1, might be a flag indicating this special "everything" playlist) | 0x883E9012A290710E |
| 46     | 1? 2?  | ? (always 0, except that it's 0x 00 01 on certain smart playlists (including folders))                                       |
| 48     | 1? 2?  | ? (same as 46 but a bigger set of smart playlists)                                                                           |
| 50     | 8      | Playlist ID of parent playlist folder (nothing to do with the [lPma](#lpma-playlist-list) section parent)                    | 0x883E9012A290710E |
| ...    |        | ?                                                                                                                            |
| 78     | 2? 4?  | Special playlist ID                                                                                                          | see below          |
| ...    |        | ?                                                                                                                            |
| 138    | 4      | Playlist modified date                                                                                                       | 3818534400         |
| ...    |        | ?                                                                                                                            |
| 174    | 2? 4?  | ? (mostly 0, otherwise mostly values \<500, but some values as high as 36k)                                                  |
| 178    | 2? 4?  | ? (repeat of previous)                                                                                                       |
| 182    | 4      | ? (a date?)                                                                                                                  |
| 186    | 4?     | ? (mostly 0x 00 00 00 01, sometimes 0x 01 00 00 01)                                                                          |
| 192    | 4?     | ? (0, 6, or 46 in decreasing frequency)                                                                                      |
| ...    |        | ?                                                                                                                            |
| 223    | 1      | Suggestion flag                                                                                                              | see below          |
| ...    |        | ?                                                                                                                            |
| 263    | 16     | Artwork UUID in [artwork.sqlite](#artworksqlite), 0 if no artwork                                                            | 0xDDAE1C...        |
| ...    |        | ?                                                                                                                            |
| 280    | 8      | ? (an ID?)                                                                                                                   |
| ...    |        | ?                                                                                                                            |
| 296    | 4?     | ? (usually 102, sometimes 0)                                                                                                 |
| 300    | 4?     | ? (usually 8, sometimes 0)                                                                                                   |
| ...    |        | ?                                                                                                                            |
| 316    | 4?     | ? (usually 1, sometimes 0)                                                                                                   |
| 320    | 4?     | ? (0, 1, or 2)                                                                                                               |
| 324    | 4      | Suggestion flag modified date, 0 if never                                                                                    | 3818534400         |
| ...    |        | ?                                                                                                                            |
| 356    | 4      | ? (almost always 2, otherwise maybe a date for 3 smart playlists)                                                            |
| ...    |        | ?                                                                                                                            |

Changing the playlist's view options updates the modified date, even though the view options are stored in the [preferences folder](#preferences-folder).

Offset 78 special playlist ID enum values:

- 0x 00 00 = all normal playlists
- 0x 00 41 = "Downloaded"
- 0x 00 04 = "Music"
- 0x 00 2F = "Music Videos"
- 0x 00 40 = "TV & Movies"
- 0x 00 1A = "Genius"
- 0x 00 13 = "Purchased"

Offset 223 suggestion flag enum values: see [itma](#itma-track)

Parents: [lPma](#lpma-playlist-list)

Children: [boma](#boma-binary-object)

Grandchildren:

- 0xCE: [ipfa (Playlist Item)](#ipfa-playlist-item)
- 0xCA: [Smart Playlist Options](#smart-playlist-options)
- 0xC9: [SLst (Smart Playlist Rules)](#slst-smart-playlist-rules)
- [Strings](#string-section):
  - 0xC8 = playlist name
  - 0xCd = generated artwork UUIDs plist (XML)

# ipfa (Playlist Item)

[Back to TOC](#table-of-contents)

Seems completely understood: X

"Apple ? playlist item"?

| Offset | Length | Meaning                                             | Examples Value(s)                         |
| ------ | ------ | --------------------------------------------------- | ----------------------------------------- |
| 0      | 4      | Section signature                                   | ipfa                                      |
| 4      | 4      | Section length                                      | 68 (always even though it's a boma child) |
| 8      | 4      | ? (always a small number, different for each entry) |
| 12     | 8      | ipfa ID                                             |
| 20     | 8      | Track ID                                            |
| ...    |        | ?                                                   |
| 44     | 8      | ipfa ID again (if last track in playlist?)          |
| ...    |        | ?                                                   |

Grandparents: [lpma](#lpma-playlist)

Parents: [boma](#boma-binary-object) (subtype 0xCE)

# Smart Playlist Options

[Back to TOC](#table-of-contents)

Seems completely understood: X

The length is always 112 bytes (the boma parent always has associated sections length 132).

| Offset | Length | Meaning                                                                           | Examples Value(s) |
| ------ | ------ | --------------------------------------------------------------------------------- | ----------------- |
| 0      | 1      | Checkbox "live updating"                                                          |
| 1      | 1      | Checkbox to enable matching rules, keeps associated information even if unchecked |
| 2      | 1      | Checkbox to enable limit                                                          |
| 3      | 1      | Limit unit                                                                        | see below         |
| 4      | 1      | Selection (ordering) method for limit                                             | see below         |
| ...    |        | ?                                                                                 |
| 8      | 4      | Limit count                                                                       |
| 12     | 1      | Checkbox "match only checked items"                                               |
| 13     | 1      | Negate selection ordering method, see below                                       | 0, 1              |
| ...    |        | ?                                                                                 |

The GUI enforces that either matching rules or the limit (offsets 1 and 2) must be enabled to save the smart playlist (otherwise it would not filter anything).

To be able to toggle the checkbox for offset 12 in the GUI, must have "Settings" → "General" → "Show" → "Song list checkboxes" checked. The checkboxes this refers to can be seen by changing "View as" to "Songs" (not in any other view).

Offset 3 limit unit enum values:

- 0x03 = items
- 0x01 = minutes
- 0x04 = hours
- 0x02 = megabytes
- 0x05 = gigabytes

Offset 4 selection method for limit enum values:

- 0x02 = random
- 0x06 = album
- 0x07 = artist
- 0x09 = genre
- 0x05 = title
- 0x1c = highest rating
  - when offset 13 is set to 1 instead of 0, negates to become lowest rating
- 0x1a = most recently played
  - when offset 13 is set to 1 instead of 0, negates to become least recently played
- 0x19 = most often played
  - ditto
- 0x15 = most recently added
  - ditto

Offset 13 is always 0 for the other offset 4 values.

Grandparents: [lpma](#lpma-playlist)

Parents: [boma](#boma-binary-object) (subtype 0xCA)

# SLst (Smart Playlist Rules)

[Back to TOC](#table-of-contents)

"Smart playList"?

Seems completely understood: X

The length is highly variable...? (Is this just because of nesting?)

| Offset | Length | Meaning                                  | Examples Value(s) |
| ------ | ------ | ---------------------------------------- | ----------------- |
| 0      | 4      | Section signature                        | SLst              |
| 4      | 4?     | ? (_not the section length_)             | 0x00010001        |
| ...    |        | ?                                        |
| 11     | 4      | Number of subsections                    |
| 15     | 1      | Match \<all/any\> of the following rules | see below         |
| ...    |        | ?                                        |

Offset 15 "match \<all/any\> of the following rules" enum values:

- 0 = all
- 1 = any

Grandparents: [lpma](#lpma-playlist)

Parents: [boma](#boma-binary-object) (subtype 0xC9)

Children:

- self (nested "Match all/any of the following rules" lists)
- [Text Match Rule](#text-match-rule)
- todo

# Text Match Rule

[Back to TOC](#table-of-contents)

Length is...?

| Offset | Length   | Meaning                            | Examples Value(s) |
| ------ | -------- | ---------------------------------- | ----------------- |
| 0      | 4?       | Field to match                     | see below         |
| 4      | 1        | Comparison method                  | see below         |
| ...    |          | ?                                  |
| 55     | 2        | Length of string in bytes          |
| 57     | variable | Criterion string encoded in UTF-16 |

Offset 0 field to match enum values:

- 3 = album
- 71 = album artist
- todo

Offset 4 comparison method enum values:

- 0x 01 00 00 02 = contains
- 0x 03 00 00 02 = does not contain
- 0x 01 00 00 01 = is (exact full match)
- 0x 03 00 00 01 = is not
- 0x 01 00 00 04 = begins with
- 0x 01 00 00 08 = ends with

This could be interpreted as a pair of byte flags, where for the first byte 01 is default, 03 negates the criterion, and each kind of comparison is a different value for the byte at the end.

Parents: [SLst](#slst-smart-playlist-rules)

# LPma (Padding?)

[Back to TOC](#table-of-contents)

"Apple Music library padding"? Appears once at the end of my library in an hsma by itself. Hasn't always been present, but a newly-created library also has it (as of December 2025).

| Offset | Length | Meaning           | Examples Value(s) |
| ------ | ------ | ----------------- | ----------------- |
| 0      | 4      | Section signature | LPma              |
| 4      | 4      | Section length    | 96                |
| ...    |        | ?                 |
| 12     | 1?     | ?                 | 6                 |
| ...    |        | ?                 |

Parents: [hsma](#hsma-section-header)

# Relevant Accompanying Files

[Back to TOC](#table-of-contents)

These are files that I referred to somewhere above because they have some direct relationship to data inside the Library.musicdb file, briefly discussed for context on that relationship, not a comprehensive description of all files that accompany Library.musicdb.

## artwork.sqlite

This [sqlite](https://sqlite.org) database, which is in the same location as Library.musicdb, seems to be used to retrieve artwork image files (either from local cache (the "artwork" and "artwork_originals" folders also in the same location) or from Apple servers) to display them. The artwork UUID present in the Library.musicdb file corresponds to values in the `artwork_id` columns. They have been formatted into text as XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX hexadecimal, which is why I think they are UUIDs specifically.

```
> sqlite3 artwork.sqlite
SQLite version ...
Enter ".help" for usage hints.
sqlite> select * from sqlite_schema;
table|version_info|version_info|3|CREATE TABLE version_info (id INTEGER PRIMARY KEY, major INTEGER, minor INTEGER, compatibility INTEGER DEFAULT 0, update_level INTEGER DEFAULT 0, device_update_level INTEGER DEFAULT 0, platform INTEGER DEFAULT 0)
table|artwork_source|artwork_source|4|CREATE TABLE artwork_source (artwork_id TEXT NOT NULL, aspect INTEGER DEFAULT 0, location_type INTEGER NOT NULL, location TEXT NOT NULL, PRIMARY KEY (artwork_id))
index|sqlite_autoindex_artwork_source_1|artwork_source|5|
table|cache_items|cache_items|6|CREATE TABLE cache_items (artwork_id TEXT NOT NULL, size_kind INTEGER NOT NULL, extension TEXT, image_hash TEXT, width INTEGER, height INTEGER, status INTEGER NOT NULL, PRIMARY KEY (artwork_id,size_kind))
index|sqlite_autoindex_cache_items_1|cache_items|7|
table|item_to_artwork|item_to_artwork|8|CREATE TABLE item_to_artwork (item_id INTEGER NOT NULL, source_kind INTEGER NOT NULL, remote_id INTEGER DEFAULT 0, artwork_id TEXT NOT NULL, PRIMARY KEY (item_id))
```

For [iAma](#iama-artist) offset 64, seems to be non-zero only when `location_type = 2` in the `artwork_source` table. The `location` is usually a URL such as "https://is1-ssl.mzstatic.com/image/thumb/Music\<number\>/v4/\<several path components with a UUID\>/\<some image name\>".

## Preferences Folder

This folder contains .plist files which seem to be the view options for:

- Playlists: files are called "Playlist\_\<playlist ID\>.plist", e.g. "Playlist_4018ae797d0cea3c.plist" — note that the bytes have been reversed compared to the Library.musicdb file, so this one has 0x 3c ea 0c... in its lpma section.
- Albums: likewise "Album\_\<album ID\>.plist"
- Special built-in lists:
  - Albums.plist
  - Artists.plist
  - RecentlyAddedMusic.plist
  - Songs.plist

# Data Stored in the Audio File

[Back to TOC](#table-of-contents)

Apple Music understands [ID3 tags](https://id3.org/id3v2.3.0). Some data is stored only in the audio file:

- ID3 version
- lyrics
- more?

and some data is stored redundantly in both the Library.musicdb file and the audio file:

- comments
- more?
