# Apple Music Library.musicdb Interface

This is a Python interface for Apple Music's Library.musicdb file, which can be used to read _and edit_ it (which makes it different from the previous projects credited below).

While making this, I also took my turn at learning more about the file format. Jump to the [Table of Contents](#table-of-contents) below for what I believe is the most complete public Library.musicdb description! It includes all of previously known information along with my own discoveries and commentary.

# Using This Code

Considering the functionality already covered by the official program, in my opinion this code is most useful for:

- making bulk changes other than those of the kind "set this field to the same value on all of these items" (which the official program can already do)
- changing things that the official program GUI does not allow you to change at all, e.g. track play count
- fixing problems created by the official program itself (usually due to bugs and mysterious "unexpected errors")

Here are some examples:

- add 5 to the play count of all songs that have a certain word in their name (the official program does not let you edit the play count, and even if you could, it would likely only allow you to set the play count to an exact value in a bulk operation)
- create a playlist with songs matching criteria other than the ones supported by built-in smart playlists, such as regular expression matching
  - possibly with multiple repeats of the same song (something that smart playlists don't do) to increase the probability of it being selected when shuffling
- automatically change songs' star ratings based on their ratio play count/skip count
- detect and repair tracks where the file path hasa become incorrect (this often happened to me when editing my library — I discovered that several hundred tracks had become disconnected from their files, and the official program just silently skips over them without saying anything about it)

I considered making a nice frontend program, but ultimately decided against it. I imagine that if one wants to do something the official program GUI cannot, then it is also likely the case that they would want to do something different from myself, and would have the necessary computer science knowledge to use this code directly. So instead, I've provided the above examples as Python scripts, and hopefully adequate documentation inside the code comments.

_Note that this code does not support the book subtype of boma sections, because, as mentioned below, my library doesn't have any I could test with, which makes me suspect they are no longer in use anyway._

_In general, I just know it works on my own library file with the types of edits I wanted to do, so I can't give any guarantees about what it does to your library file. For this reason I've made it automatically make backups when you use the program to edit your library, unless you specifically turn them off. They will be called e.g. "Library backup 2026-01-01T00.00.00.musicdb" (if you saved the edited version at midnight of January 1, 2026) and placed in the same folder as Library.musicdb._

# Acknowledgements

- https://home.vollink.com/gary/playlister/musicdb.html (Gary Vollink) and everyone credited by him at the bottom
- https://github.com/rinsuki/musicdb2sqlite
- https://github.com/jsharkey13/musicdb-to-json (also copied a small amount of code from here, see the comments in my code for details)

> "If I have seen further, it is by standing on the shoulders of giants."

-Isaac Newton

This quote feels appropriate, since I am the fourth in this line where each person credited the others before themself.

# Table of Contents

- [Investigation Tips](#investigation-tips)

---

- [General Notes](#general-format-notes)
- [Consistent Naming of Fields](#consistent-naming-of-fields)

---

- [Time Zone Handling](#time-zone-handling)

---

- [Encryption and Compression](#encryption-and-compression)
- [Section Structure](#section-structure)

---

- [hfma (File Header)](#hfma-file-header)
- [hsma (Section Header)](#hsma-section-header)

---

- [boma (Binary Object)](#boma-binary-object)
- [String Section](#string-section)
- [Raw String](#raw-string)

---

- [Global Counter](#global-counter)

---

- [plma (Library Master)](#plma-library-master)
- [1F6](#1f6)
- [1FF](#1ff)

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
- [SLst (Smart Playlist Rules List)](#slst-smart-playlist-rules-list)
- [Smart Playlist Rule](#smart-playlist-rule)

---

- [LPma (Padding?)](#lpma-padding)

---

- [Accompanying Files](#accompanying-files)
- [Data Stored in the Audio File](#data-stored-in-the-audio-file)

# Investigation Tips

[Back to TOC](#table-of-contents)

Methods in order from best to worst IMO:

- dump the binary, change something in the GUI, and dump the binary again to compare what's changed in a hex editor — if only one thing has changed, that's definitely the byte representation of the change you made in the GUI
  - modification dates, or in general other related data, will often change also, so it helps if you already know what those are and can ignore them
  - it is helpful to narrow focus to the section type of the thing you changed, e.g. hfma/plma for settings on the entire library, itma for tracks, etc.
- explore what values are common at certain offsets inside of your library (the larger the better) for a hint at the value's meaning
  - see "Interpreting unknown values" below
  - see how different items containing certain values are related (e.g. same name, same album, same playlist...)
  - search in the GUI for appearances of a value on items that have it (e.g. pick out some tracks that have a certain value, find their name, and look at their properties in the GUI to find that value) — works well for dates and counts, but would be hard to figure out enums this way
- change values in the binary arbitrarily and launch the official program to see if there is any effect
  - I have not tried this method because I imagine it would be very unfruitful
  - I assume you will just cause the library to be detected as corrupt most of the time by doing this
  - if not, it will be difficult to figure out what, if anything has changed
  - the only cases where this would be useful that wouldn't also be covered by the first method would be values you cannot edit in the GUI

Interpreting unknown values:

- a value with sparse bits like 0x 03 01 00 01 is usually a collection of bit or enum flags
- a low value like 25, 304, etc. is usually some kind of count
  - a value that has several ff bytes at the end is likely a negative value of low magnitude represented as a signed integer
- a value with dense bits like 0x cd 3a 45 18 is usually some kind of ID or hash
- with one exception to the previous: dates are expressed in seconds since 1904-01-01T00:00 (former MacOS epoch), therefore values in the high 3 billions (or higher if you are reading this in the 2030s and beyond) should be suspected as dates
- try throwing numbers (in decimal) into a web search "site:music.apple.com \<number\>" if you think it might be an Apple Music store ID (although I think I found all of those already)
- if the value 0 is most common, then 1, then 2, etc. (or beginning at some other value), then this is likely a counter value, but only over a subset of the sections you took the value count over

To determine the size of an unknown section that doesn't have the size in the usual place:

- for data in a list:
  - dump the binary with no entries, add an entry, dump again and see how much data got added
  - or create 2 identical entries and see how much space is in between the data repeating (this is what I did for smart playlists initially)
- manipulate change the size of the section and try to see if any data has changed by the amount the size has changed
  - easiest with string data
  - may be hard to filter out other changes that occur simultaneously, especially since size is one of the first things one must learn about a new section type

# General Format Notes

[Back to TOC](#table-of-contents)

How can we successfully edit the file when large parts of the file format remain a mystery?

- Firstly, I have discovered a lot more about the format.
- Secondly, making simple edits can be done easily enough by preserving all of the unknown data as-is (this is the major difference with previous projects, which did not preserve every byte in converting to another format).
- Finally, and perhaps most importantly, it turns out that official Apple Music program is actually quite lenient. Actually, because of this, in my opinion Gary Vollink was being overly pessimistic when he said "this information will NOT be enough to create or even manipulate a musicdb externally" — most manipulations I can think of could have been done without any of my new discoveries. As long as the metadata about the [section structure](#section-structure) is correct, it can handle plenty of cases where parts of the data are uninitialized (it will set correct values itself, and maybe it doesn't even read them at all in some cases), for example:

  - the song, playlist, album, and artist counts in [hfma](#hfma-file-header) do not need to be set
  - likewise the track count of a [playlist](#lpma-playlist) does not need to be set
  - randomized ID numbers do not need to be initialized (although if its an ID number referring to something else, e.g. [playlist item](#ipfa-playlist-item) referring to a [track](#itma-track) by its ID, that obviously _does_ have to be initialized correctly)
  - 0 is fine as a default for a lot of values in general (it is almost always the default used by the official program)

- I will assume little-endianness because nobody has documented a case of big-endianness, even though Gary Vollink speculates it might be possible. Therefore 0x 04 03 02 01 interpreted as an unsigned int is 16909060, not 67305985.
  - UTF-16 strings are always little-endian.
- Integers are almost always unsigned, it will be noted where this is not the case.
- Booleans (checkboxes) are always 1 byte, 0 = false/not checked, 1 = true/checked.
- In the tables below, an offset "..." means all of the offsets in between the previous and next entries (or until the end of the section if at the end) were always 0 in my library (unless I missed any).
  - It is tempting to assume that these are just reserved empty space — but this is not always the case! As I discovered, there are many cases where 0 is the default value indicating that some feature is not used, a pointer is not assigned, etc., and your library file will always contain 0 there if you happen to have never used that feature! For example, did you know that you can favorite artists, albums, and playlists as well as tracks? Neither did I until after exploring every nook and cranny of the GUI for this project, and all of those bytes were 0s until I found them.
- "(a?)" is shorthand for "(always?)", noting that an offset always has the value given in the example in my library (this is not given comprehensively, I may have missed some cases). However, I would assume that in all of these cases another value is possible, otherwise why isn't it 0?
  - In principle, section lengths could be different between sections of the same type. In practice, however, they are always the same for a certain section type, _with the only exceptions being sections containing string data_. Therefore I will not mark these with (a?) and you may assume the example value is the one and only value that ever appears other than this exception.
  - Obviously the section signature will also always be the same for a certain section type, almost by definition.

# Consistent Naming of Fields

[Back to TOC](#table-of-contents)

Inside the code, I use these conventions for naming fields (offsets) to keep things consistent:

- in general, start with the data type
- for dates, always start with "date\_"
  - then always follow with "created", "added", "modified", "last\_..." as appropriate
  - then, if applicable, what has been modified (e.g. "date_modified_suggestion_flag", whereas just "date_modified" means the date when whatever this is a field of as a whole has been modified)
- for checkboxes, always start with "checkbox\_"
  - there are other booleans, this is only if the GUI presents a checkbox to the user
- some fields have both a number and a total, e.g. the disc number and disc total, these will be named "...\_number" and "...\_total" respectively, e.g. "disc_number" and "disc_total"
  - likewise for counts
- for sorting fields, "sort\_" goes first
- for UUIDs, [Python `struct`](https://docs.python.org/3/library/struct.html) doesn't have a format specifier for 16 bytes, therefore I split them into 2 8-byte fields "uuid_1\_..." and "uuid_2\_..."
- for all IDs, "id\_" goes first
  - for IDs that are in the Apple Store, "id_apple_music\_..."
  - for IDs from iTunes, "id_itunes\_..."
- use the word "size" for byte lengths
  - "total_size" means of a sum of multiple sizes
- "plist\_" for XML plist strings
- some specific, recurring fields:
  - "suggestion_flag" for favorite/suggest less
  - "star_rating" for star ratings (as opposed to e.g. "content_rating", less confusing than just "rating")

For some fields I provide alias names where either can be used, e.g. "name" and "title".

# Time Zone Handling

[Back to TOC](#table-of-contents)

Dates are almost always stored using the local time on the computer. [hfma](#hfma-file-header) contains a time zone offset that can be used to convert to another time zone. (What happens if the computer's time zone is changed?)

# Encryption and Compression

[Back to TOC](#table-of-contents)

To get what I refer to as the "raw" library bytes from the file as saved on disk by the official program:

- The outer [hfma](#hfma-file-header) section is saved plain and contains the required metadata.
- The crypt size is:
  - The file size if file size \< max crypt size in hfma
  - Otherwise file size - outer hfma length - ((file size - outer hfma length) % 16)
  - The max crypt size always seems to be 102400, I was not able to find any other values accepted by the official program (not that there's any reason to use a different one, so I didn't search that hard)
- Starting after the outer hfma, decrypt \<crypt size\> bytes using AES128-ECB and the encryption key (see code)
- Concatenate the remaining bytes in the file after the encrypted portion onto the decrypted bytes
- Decompress the result with zlib
  - Experimentally, the official program uses compression level 1 (best speed), but it also seems to accept any compression level (not that there's any particular reason to use another compression level when the official program will resave the library itself the next time you open it)
- Concatenate the decompressed result onto the outer hfma header

The remainder of this document describes the raw library bytes.

# Section Structure

[Back to TOC](#table-of-contents)

The file is divided into what most have previously called "sections". Sections may have subsections, creating a tree structure (so I also call them "children"). If section A has subsections B and C, and B has subsections D and E, then they will appear in the file in the order A B D E C. In my code, I treat the outer [hfma](#hfma-file-header) section as the tree's root (thus its class name is `Library`, and the class name `hfma` is used only for the inner one).

In almost all cases, the order of the children does not matter because one of the following is true:

- there is only one child
- the data inside the subsection identifies it, e.g. section signature or subtype
- the GUI uses other data inside to sort at runtime, but saves data in some arbitrary order
- [one exception](#ipfa-playlist-item)

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
| 12      | 4      | Section subtype (enum value that hints at the subsection type)                        | 3                 |

Using either associated sections length (which I call "total size" in some places in my code) or number of subsections, it is possible to determine where the subsections end and the next section at either the same level or a higher one begins (a section with subsections usually must have at least one of these). Some kinds of sections have both of these, which is why number of subsections is occasionally at offset 12 instead of 8. When this is the case, my code prefers to use the associated sections length, because it is possible to use this to continue on afterward even in the case of mysterious subsections that might appear in the future.

# hfma (File Header)

[Back to TOC](#table-of-contents)

Seems completely understood: X

Speculation: "Apple Music file header" (acronym reversed due to endianness)? Or maybe "header (of) file, media (data type)" or "header (of) file master"?

There is one version of this section outside of the encryption/compression process, containing the metadata needed to reverse it. There is also a version of this section inside, which is _mostly_ a copy of the outer one where it has non-zero values. Maybe it's used to verify correct decryption/decompression.

In the last column of the table below, which is unique to this section type:

- yes = the data is duplicated
- no = non-zero data in the outer hfma is zero in the inner hfma
- different = both have non-zero values but not the same value as each other

| Offset | Length | Meaning                                                                                                                        | Examples Value(s)                               | Duplicated in Inner Copy |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------- | ------------------------ |
| 0      | 4      | Section signature                                                                                                              | hfma                                            | yes                      |
| 4      | 4      | Section length (bytes)                                                                                                         | 160                                             | yes                      |
| 8      | 4      | File length in bytes (when encrypted/compressed, not raw, therefore this cannot be considered as "associated sections length") | 5767                                            | no                       |
| 12     | 2      | File format major version                                                                                                      | 21                                              | yes                      |
| 14     | 2      | File format minor version                                                                                                      | 1                                               | yes                      |
| 16     | 32     | Apple Music version as null-terminated string                                                                                  | 1.0.1.37                                        | yes                      |
| 48     | 8      | Library ID                                                                                                                     | 0xF60BBBD97C7D8F41                              | yes                      |
| 56     | 4      | musicdb file type                                                                                                              | see below                                       | no                       |
| 60     | 4      | ?                                                                                                                              | 20 (a?)                                         | yes                      |
| 64     | 4      | ? (not zero but different between inner and outer, might be bit flags)                                                         | 0x 02 01 01 00 (outer) / 0x 02 00 00 00 (inner) | different                |
| 68     | 4      | Song count                                                                                                                     | 136                                             | no                       |
| 72     | 4      | Playlist count                                                                                                                 | 15                                              | no                       |
| 76     | 4      | Album count                                                                                                                    | 459                                             | no                       |
| 80     | 4      | Artist count                                                                                                                   | 24                                              | no                       |
| 84     | 4      | Max crypt size                                                                                                                 | 102400 (a?)                                     | no                       |
| 88     | 4      | Library time offset in seconds (i.e. timezone)                                                                                 | -14400 (US/NY) (_signed value_)                 | yes                      |
| 92     | 8      | Your Apple Store account ID (0 when not signed in)                                                                             | 0xA10D876FF3940021                              | yes                      |
| 100    | 4      | Library modification date                                                                                                      | 3658272271                                      | yes                      |
| 104    | 4      | ?                                                                                                                              | 1                                               | no                       |
| 108    | 8      | Library ID (if from iTunes import)                                                                                             | repeat of offset 48, or 0                       | yes                      |
| 116    | 4      | ?                                                                                                                              | 0x 23 01 00 00                                  | no                       |
| 120    | 8      | ? (not repeated anywhere else in file; observed changing chaotically like a hash when other things are edited)                 | 0x 3F F2 06 1B 6E 62 23 1E                      | yes                      |
| ...    |

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
| ...    |

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
| 0      | 4      | Section signature          | boma              |
| 4      | 4      | Section length             | 20                |
| 8      | 4      | Associated sections length | 160               |
| 12     | 4      | Section subtype            | 3                 |
| ...    |

Here is a major disagreement with Gary Vollink's table: he, and therefore everyone after him but before me, believed that boma sections broke the usual pattern, and thought boma sections had at offset 4 a mysterious value "always 0x14", while the section length was at offset 8 instead of at 4 as usual. But I believe that boma sections are _not_ the ones that break the pattern. The realization for me came from looking at [smart playlist rules](#slst-smart-playlist-rules-list), which clearly had a section header "SLst" the repeated once for each rule, along with noticing that Gary Vollink came so close to the same realization with boma sections of subtype 0xce, containing [ipfa](#ipfa-playlist-item) subsections — in that case, he labeled offset 4 "subdata start" but still called offset 8 the section length. The problem is that _the children_ of boma sections break the pattern — many do not have a signature, at least not one made of 4 printable ASCII characters, and offset 4 is almost never the section length. This is why I speculate that the "bo" means "object binary"/"binary object", as an indication that the children usually do not follow the usual section-based format, even though obviously everything is in binary.

For children of boma, this means that all offsets listed on Gary Vollink's page or in anyone else's code will be 20 greater than the ones I am listing.

From a practical point of view this doesn't change that much because you will often still need the associated sections length to make sure to read the correct amount of subsection data, and the subtype to know how to interpret it, but at least it explains the "always 0x14", and makes the pattern break less strange in that it is complete, dramatic, and more obviously intentional rather than seemingly very subtle for no good reason.

In almost all cases, a boma section's subtype should not be shared by any of its siblings ([one known exception](#ipfa-playlist-item)). If there are somehow 2 or more (due to external tampering or [a bug](#track-numerics)), only the first one gets used by the official program, and it may or may not discard the others.

Parents:

- [plma](#plma-library-master)
- [iama](#iama-album)
- [iAma](#iama-artist)
- [lpma](#lpma-playlist)

Children: Depends on subtype. See each of the parents, which list their grandchildren. But common ones include:

- [String Section](#string-section)
- [Raw String](#raw-string)
- Book? (See Gary Vollink's page for a description. I don't have any in my Library.musicdb file, so I couldn't test anything on them and I didn't write any code for them. However, some boma subtypes that Gary Vollink lists as having book data inside (0x1FC, 0x1FD, 0x200) have the normal string format instead in my library, so I suspect they are no longer in use, which makes sense because they seem unnecessarily long and complicated.)

# String Section

[Back to TOC](#table-of-contents)

Seems completely understood: X

| Offset | Length   | Meaning                                                                                                                                                 | Examples Value(s) |
| ------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| 0      | 4        | String encoding (could be interpreted as a "signature"), 1 for UTF-16 and 2 for UTF-8 (Would the program accept the other encoding if this is changed?) | 1, 2              |
| 4      | 4        | Section length _starting from offset 16_ (i.e. the string length)                                                                                       | 100               |
| 8      | 4?       | Parent subtype counter (see below)                                                                                                                      |
| ...    |
| 16     | variable | The string data in the specified encoding                                                                                                               | any string        |

Offset 8: counts up starting from 0, separately for each parent subtype value. For example, you might have in this order:

- parent with subtype 0x12C, counter 0
- 0x12C, 1
- 0x12D, 0
- 0x12C, 2
- 0x12C, 3
- 0x12D, 1
- 0x12E, 0
- 0x12D, 2

Parents: [boma](#boma-binary-object), many different subtypes

# Raw String

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

These are in UTF-8 or UTF-16. It is not clear why some strings are inside of sections, and some are just given raw. The only surefire way to infer that data is a raw string and which encoding it is in is the parent boma sections's subtype, and the only surefire way to infer the string's length is the parent boma section's associated section length.

| Offset | Length   | Meaning     | Examples Value(s)            |
| ------ | -------- | ----------- | ---------------------------- |
| 0      | variable | string data | "\<?xml=...", "C:/Users/..." |

Parents: [boma](#boma-binary-object), many different subtypes

# Global Counter

[Back to TOC](#table-of-contents)

I have discovered that there is a counter running through many of the section types below, so I am calling it the "global counter". It increments by 1 in the order the sections appear in the file.

- (I do not believe I have discovered where the counter starts presumably at 0 or 1, because the following began at 96 in a small library, and at 1002 in a larger one, suggesting a correlation with how many of something else is present in the library; it does not seem like it begins in [iama](#iama-album) or [iAma](#iama-artist) even though those seem the obvious place as neither have any offsets showing counter behavior)
- [itma](#itma-track) offset 24
- [track numerics](#track-numerics) offset 0
- [lpma](#lpma-playlist) offset 26
- [ipfa](#ipfa-playlist-item) offset 8

The values for itma and track numerics are alternating by nature as each itma always has one track numerics grandchild. Likewise, since ipfa's are grandchildren of lpma, there will be one counter value taken by an lpma followed by a streak of them taken by ipfa grandchildren.

The counter seems to be 4 bytes since it is followed by unrelated data inside of some sections after that many bytes.

This finally explains to me why these offsets would chaotically change after unrelated edits, why they are low-ish numbers, and why they are often consecutive/incrementing by 2 depending on the section type.

The purpose of this counter remains unknown. Apparently, when creating data from scratch, it is not necessary to set this value.

# plma (Library Master)

[Back to TOC](#table-of-contents)

Seems completely understood: X

"Apple Music library playlist"? (I believe the entire library used to be encoded as a special kind of playlist in iTunes.)

Appears only once.

| Offset | Length | Meaning                                                                                                                 | Examples Value(s)  |
| ------ | ------ | ----------------------------------------------------------------------------------------------------------------------- | ------------------ |
| 0      | 4      | Section signature                                                                                                       | plma               |
| 4      | 4      | Section length                                                                                                          | 194                |
| 8      | 4      | Number of subsections                                                                                                   | 6                  |
| ...    |
| 24     | 1      | Checkbox "Settings" → "General" → "Show" → "Songs list checkboxes"                                                      |
| ...    |
| 52     | 4      | ? (0x 00 00 02 00 in my library)                                                                                        |
| 58     | 8      | Library ID                                                                                                              | 0xF60BBBD97C7D8F41 |
| ...    |
| 68     | 4      | ? (0x 00 00 08 00 in my library)                                                                                        |
| ...    |
| 92     | 8      | Library ID (again)                                                                                                      | 0xF60BBBD97C7D8F41 |
| ...    |
| 104    | 4      | ? (found repeated at offset 244 of [itma](#itma-track), inside [track numerics](#track-numerics) at offset 200 and 280) | 0x 78 A0 72 78     |
| ...    |
| 128    | 4      | ? (2 in mine)                                                                                                           |
| ...    |
| 136    | 4      | ? (256 in mine)                                                                                                         |
| ...    |
| 144    | 4      | ? (0x 00 00 01 01 in mine)                                                                                              |
| 148    | 1      | Checkbox "Settings" → "Files" → "Keep media folder organized"                                                           |
| ...    |
| 160    | 4      | ? (0x 00 00 02 00 in mine)                                                                                              |
| ...    |
| 168    | 4      | ? (0x 00 00 01 00 in mine)                                                                                              |
| ...    |
| 176    | 4      | ? (0x 00 00 08 00 in mine)                                                                                              |
| ...    |

Parents: [hsma](#hsma-section-header)

Children: [boma](#boma-binary-object)

Grandchildren:

- 0x1F6 = [1F6](#1f6)
- 0x1FF = [1FF](#1ff)
- [Strings](#string-section):
  - boma subtype 0x1F8 = media folder URI ("file://localhost/C:/...") (UTF-16)
- [Raw Strings](#raw-string)
  - 0x1FC = imported iTunes .itl file (UTF-8)
  - 0x1FD = media folder path (UTF-16)
  - 0x200 = exactly the same as 0x1FD

# 1F6

[Back to TOC](#table-of-contents)

Seems completely understood: X

1F6 is a (hopefully) temporary name derived from the boma parent subtype.

Length is always 20.

| Offset | Length | Meaning                                                                                        | Examples Value(s)                  |
| ------ | ------ | ---------------------------------------------------------------------------------------------- | ---------------------------------- |
| 0      | 4?     | ? (not a signature, not a section length)                                                      | 0x 01 00 14 00, 0x 00 01 00 25     |
| 4      | 16?    | ? (an ID? a hash? not found anywhere else in library, nor in [artwork.sqlite](#artworksqlite)) | 0x00DA6A686DC46CA4CBCB01A6671386BF |

Grandparents: [plma](#plma-library-master)

Parents: [boma](#boma-binary-object) (subtype 0x1F6)

# 1FF

[Back to TOC](#table-of-contents)

Seems completely understood: X

1FF is a (hopefully) temporary name derived from the boma parent subtype.

Length is always 44.

? (contains 2 copies of library ID in my library, only 1 copy in a fresh one; something to do with iTunes?) (_note that this appears to have a subsection with the signature for a UTF-16 string signature but it isn't one_)

| Offset | Length | Meaning                           | Examples Value(s)                                                         |
| ------ | ------ | --------------------------------- | ------------------------------------------------------------------------- |
| 0      | 8?     | ?                                 | 1 (a?) (_do not confuse with [UTF-16 string](#string-section) signature_) |
| 8      | 8      | Library ID                        |
| 16     | 8      | Library ID again sometimes (why?) |
| ...    |

Grandparents: [plma](#plma-library-master)

Parents: [boma](#boma-binary-object) (subtype 0x1FF)

# lama (Album List)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music album list"?

Appears only once.

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Section signature     | lama              |
| 4      | 4      | Section length        | 48                |
| 8      | 4      | Number of subsections | 1234              |
| ...    |

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
| 24     | 4      | ? (usually 0x 02 00 00 01, sometimes 0x 02 01 00 01)                                                                                                   |
| 28     | 4      | ?                                                                                                                                                      | 1 (a?)              |
| 32     | 8      | Track ID of first track in album, but sometimes 0 (is it possible to have an empty album?)                                                             | 0xC89ECA05FB184E3E  |
| 40     | 1      | Star rating (1 star = 20, 5 stars = 100)                                                                                                               | 20                  |
| 41     | 1      | Album inheritance of star rating from its songs                                                                                                        | see below           |
| 42     | 1      | Suggestion flag                                                                                                                                        | see below           |
| ...    |
| 64     | 8      | Album ID again, but sometimes 0 (usually 0 for newer albums? iTunes ID?)                                                                               | repeat of offset 16 |
| ...    |
| 96     | 4      | Suggestion flag modified date                                                                                                                          |
| 100    | 4      | Last played (most recent last played date of any track in the album, 0 if all never played)                                                            | 3818534400          |
| 104    | 4      | Album ID in Apple Music store - plug into the end of the URL "https://music.apple.com/album/..." as decimal - 0 if a custom album                      |
| ...    |
| 120    | 4      | ? (nearly always 2, but rarely otherwise found duplicated at offset 120 of [iAma (Artist)](#iama-artist) and nowhere else, might be a date when not 2) |
| ...    |

Offset 41 album inheritance of star rating enum values:

- 0x01 = album is rated directly by the user, _not_ inheriting
- 0x20 = album is _not_ rated directly by the user and its rating has been calculated as a (rounded) average of the star rating of its songs

Although this can also work in reverse — the direct star rating of an album is inherited by songs inside that lack a direct rating from the user — that doesn't get stored anywhere inside the file, presumably because it is easier to calculate (just copied rather than being an average).

Offset 42 suggestion flag enum values: see [itma](#itma-track)

Parents: [lama](#lama-album-list)

Children: [boma](#boma-binary-object)

Grandchildren:

- [Strings](#string-section):
  - 0x12C = album name (UTF-16)
  - 0x12D = artist name (UTF-16)
  - 0x12E = album artist name (UTF-16)

# lAma (Artist List)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music artist list"?

Appears only once.

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Section signature     | lAma              |
| 4      | 4      | Section length        | 100               |
| 8      | 4      | Number of subsections | 3                 |
| ...    |

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
| 16     | 8      | Artist ID                                                                                                                                                      | 0xAAE367957FF01CEC                     |
| 24     | 4      | ?                                                                                                                                                              | 2 (a?)                                 |
| 28     | 4      | ?                                                                                                                                                              | 1 (a?)                                 |
| ...    |
| 52     | 4      | Artist ID in Apple Music store - plug into the end of the URL "https://music.apple.com/artist/..." as decimal - 0 if a custom artist                           | 461932 ("It's the Final Countdown...") |
| ...    |
| 60     | 4      | Suggestion flag modified date                                                                                                                                  |
| 64     | 16     | Artwork UUID in [artwork.sqlite](#artworksqlite), only for remote images, see that section for details                                                         | 0xDDAE1C...                            |
| 80     | 8      | Artist ID again, but sometimes 0 (iTunes?)                                                                                                                     | repeat of 16                           |
| ...    |
| 96     | 4      | ? (almost always 0 but sometimes 45)                                                                                                                           |
| 100    | 1      | ? (almost always 0 but sometimes 5)                                                                                                                            |
| 101    | 1      | Suggestion flag                                                                                                                                                |
| ...    |
| 103    | 1      | ? (always 1)                                                                                                                                                   |
| 104    | 4      | ? (almost always 0 but sometimes 1)                                                                                                                            |
| ...    |
| 120    | 4      | ? (almost always 2, but rarely otherwise see [iama](#iama-album) offset 120, the set of values found here are a superset of those, might be a date when not 2) |
| ...    |

Offset 101 suggestion flag enum values: see [itma](#itma-track)

Parents: [lAma](#lama-artist-list)

Children: [boma](#boma-binary-object)

Grandchildren:

- [Strings](#string-section):
  - 0x190 = artist name (UTF-16)
  - 0x191 = artist name sort (UTF-16)
- [Raw Strings](#raw-string)
  - 0x192 = artwork URL plist (XML) (UTF-8)

# ltma (Track List)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music track list"?

Appears only once.

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Section signature     | ltma              |
| 4      | 4      | Section length        | 92                |
| 8      | 4      | Number of subsections | 3                 |
| ...    |

Parents: [hsma](#hsma-section-header)

Children: [itma](#itma-track)

# itma (Track)

[Back to TOC](#table-of-contents)

Seems completely understood: X

"Apple Music track item"?

| Offset  | Length  | Meaning                                                                                                                                                                                                                                    | Examples Value(s)                        |
| ------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------- |
| 0       | 4       | Section signature                                                                                                                                                                                                                          | itma                                     |
| 4       | 4       | Section length                                                                                                                                                                                                                             | 376                                      |
| 8       | 2? 4?   | ? (usually in range 1000-3000, observed changing when equalizer is set but doesn't matter which equalizer, for other reasons as well, often shared between a few tracks in the same album but also between many unrelated ones)            | 0x F3 0C 00 00                           |
| 12      | 4       | Number of subsections                                                                                                                                                                                                                      | 18                                       |
| 16      | 8       | Track ID                                                                                                                                                                                                                                   | 0xD5F6F65777A704BC                       |
| 24      | 4       | See [Global Counter](#global-counter)                                                                                                                                                                                                      |
| ...     |
| 30      | 1       | Checkbox "Skip when shuffling"                                                                                                                                                                                                             | 0 or 1                                   |
| 31      | 1       | ? (usually 1, but sometimes 0, looks like another boolean, observed changing from 0 to 1 on first play of a song)                                                                                                                          |
| ...     |
| 33      | 1       | ? (usually 0, but sometimes 1, looks like another boolean)                                                                                                                                                                                 |
| ...     |
| 35      | 1       | ? (always 1, looks like another boolean given the context)                                                                                                                                                                                 |
| ...     |
| 38      | 1       | Checkbox "Album is compilation"                                                                                                                                                                                                            |
| ...     |
| 42      | 1       | Checkbox disabled ("Songs list checkboxes") - see below                                                                                                                                                                                    |
| ...     |
| 47      | 1       | ? (almost always 0, rarely 1, likely another boolean)                                                                                                                                                                                      |
| ...     |
| 50      | 1       | Checkbox "Remember playback position"                                                                                                                                                                                                      |
| 51      | 1       | Checkbox "Show composer in all views"                                                                                                                                                                                                      |
| 52      | 1       | Checkbox "Use work & movement", keeps associated information even if unchecked (only affects display)                                                                                                                                      |
| 53      | 1       | ? (almost always 0, sometimes 1, likely another boolean)                                                                                                                                                                                   |
| ...     |
| 55      | 1       | ? (usually 1, sometimes 0, likely another boolean, observed changing from 0 to 1 on first play of a song)                                                                                                                                  |
| ...     |
| 57      | 1       | Downloaded                                                                                                                                                                                                                                 | see below                                |
| 58      | 1       | Purchased (boolean)                                                                                                                                                                                                                        |
| 59      | 1       | Content rating                                                                                                                                                                                                                             | see below                                |
| ...     |
| 62      | 1       | Suggestion flag                                                                                                                                                                                                                            | see below                                |
| ...     |
| 64      | 1       | ? (almost always 0, sometimes 1, likely another boolean)                                                                                                                                                                                   |
| 65      | 1       | Star rating (1 star = 20, 5 stars = 100)                                                                                                                                                                                                   | 20                                       |
| 66-72   | 1 each? | ? (see example values)                                                                                                                                                                                                                     | 0x80, 0x81, 0x1, 0x3                     |
| 82      | 2       | Beats per minute                                                                                                                                                                                                                           | 144                                      |
| 84      | 2       | Disc number of this track                                                                                                                                                                                                                  | 1                                        |
| 86      | 2       | Total movements (denominator for offset 88)                                                                                                                                                                                                | 5                                        |
| 88      | 2       | Movement number of this track                                                                                                                                                                                                              | 3                                        |
| 90      | 2       | Total discs (denominator for offset 84)                                                                                                                                                                                                    | 3                                        |
| 92      | 4       | ? (almost always 0, but otherwise looks like a small signed value)                                                                                                                                                                         | 0, 255, -1, 136, 75, -128, 153, 89, -230 |
| 96      | 4       | ? (not 0 only for purchased tracks, when not 0 looks like an ID, however not unique, can be shared between itma's in the same album, but not repeated elsewhere)                                                                           |
| ...     |
| 108     | 4?      | ? (always 1 in my library)                                                                                                                                                                                                                 |
| 112     | 4?      | ? (always 1 in my library)                                                                                                                                                                                                                 |
| 116     | 2       | Total tracks (denominator for offset 160)                                                                                                                                                                                                  | 3                                        |
| ...     |
| 148     | 4       | Playback start position in milliseconds (0 for not set)                                                                                                                                                                                    | 1100                                     |
| 152     | 4       | Playback stop position in ms (0 for not set)                                                                                                                                                                                               | 5000                                     |
| ...     |
| 160     | 2       | Track number                                                                                                                                                                                                                               | 2                                        |
| ...     |
| 168     | 4       | Track year                                                                                                                                                                                                                                 | 2015                                     |
| 172     | 8       | Album ID (see [iama](#iama-album) offset 16)                                                                                                                                                                                               |
| 180     | 8       | Artist ID (see [iAma](#iama-artist) offset 16)                                                                                                                                                                                             |
| 188     | 4       | Artist ID in Apple Music store (see [iAma](#iama-artist) offset 52)                                                                                                                                                                        |
| ...     |
| 220     | 8       | ? (not 0 only for songs purchased from Apple Music, repeated at 320 of the same section, 328 of a [track numerics](#track-numerics), values for tracks in the same album are close together and often consecutive, might be another ID)    |
| ...     |
| 244     | 4       | ? (see [plma](#plma-library-master) offset 104)                                                                                                                                                                                            |
| ...     |
| 252     | 4       | ? (0x 00 00 03 00 for purchased songs, otherwise 0)                                                                                                                                                                                        |
| 256     | 16      | Artwork UUID in [artwork.sqlite](#artworksqlite), whichever is the "default" (since you can attach multiple), 0 if none                                                                                                                    | 0xDDAE1C...                              |
| 272     | 8       | Track ID again sometimes (why?)                                                                                                                                                                                                            |
| 280-308 | 4? each | ? (for 280, always the same value for tracks with the same title, no matter what album, tiny hash of the title? for all, always a multiple of 1000, observed changing from 0 to sonething else the first time a song is played or skipped) |
| 308     | 4       | ? (always 6, 0, 11, 17, in descending order of frequency)                                                                                                                                                                                  |
| ...     |
| 320     | 8       | ? (see offset 220)                                                                                                                                                                                                                         |
| 328     | 4       | ? (almost always 3, otherwise 5)                                                                                                                                                                                                           |
| ...     |
| 336     | 4       | Suggestion flag modified date, 0 if never                                                                                                                                                                                                  |
| ...     |
| 344     | 4       | ? (always 0 or 1)                                                                                                                                                                                                                          |
| 348     | 4       | ? (always 0, 1, or 2)                                                                                                                                                                                                                      |
| 352     | 4       | Date added of the most recently added track, only on that track, otherwise 0                                                                                                                                                               |
| ...     |

Offset 42: The checkboxes this refers to can be seen by:

- Checking "Settings" → "General" → "Show" → "Song list checkboxes"
- Changing "View as" to "Songs" (the checkboxes do not appear in any other view, but other views will show the song faded out if disabled)

This will also enable you to toggle the checkbox "match only checked items" on smart playlists. _This is stored with the reverse convention of other checkboxes: 0 = checked, 1 = unchecked (disabled)_. For songs that are disabled, they will never come up in the queue on their own, unless they are specifically played first (then they _can_ come up again when the songs repeat). Basically, this is a stronger version of "skip when shuffling" because it also applies when not shuffling. Additionally, for smart playlists with "match only checked items" enabled, the unchecked items are not only disabled from playing, but will not be included in the playlist at all.

Offset 57 downloaded enum values:

- 0x03 = not downloaded (only possible for songs purchased from Apple Music)
- 0x01 = downloaded (including all files you added to Apple Music that were not purchased from it)

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
- [Strings](#string-section) (assume UTF-16 unless specified as UTF-8; not exhaustive since I don't have some of these):
  - 0x2 = title
  - 0x3 = album
  - 0x4 = artist
  - 0x5 = genre
  - 0x6 = kind - e.g. "MPEG audio file"
  - 0x7 = equalizer - always a UTF-16 string that looks like "#!#\<number\>#!#" where the number is different for each equalizer option, strange that this is not a single-byte enum
  - 0x8 = comments
  - 0xB = URL - only present for downloaded tracks, URL-encoded version of the file path "file:///C:/Users..." (UTF-8)
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
  - 0x3C = purchaser name - only present for downloaded tracks
  - 0x3F = work name
  - 0x40 = movement name
  - 0x43 = file path - only present for downloaded tracks
  - 0x12F = series title
- [Raw Strings](#raw-string)
  - 0x36 = artwork plist (XML) (UTF-8)
  - 0x38 = redownload parameters plist (XML) (UTF-8)

# Track Numerics

[Back to TOC](#table-of-contents)

Seems completely understood: X

The length is always 364 bytes (the boma parent always has associated sections length 384).

| Offset | Length  | Meaning                                                                                                                                                                             | Examples Value(s)                                                                    |
| ------ | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 0      | 4       | See [Global Counter](#global-counter)                                                                                                                                               |
| 4      | 4?      | ? (repeat of download flag from [itma](#itma-track) offset 57?)                                                                                                                     |
| 8      | 8       | ? (an ID? doesn't appear elsewhere)                                                                                                                                                 |
| 16     | 4?      | ?                                                                                                                                                                                   | 1 (a?)                                                                               |
| 20     | 4?      | ? (0x 00 01 01 00, sometimes 0, a pair of bit flags? observed changing from 0 to 1 on first song play/skip)                                                                         |
| 24     | 4?      | ? (half the time 0, half the time 0x 00 00 00 01)                                                                                                                                   |
| ...    |
| 33     | 1?      | ? (another bit flag? very rarely 1)                                                                                                                                                 |
| ...    |
| 36     | 1?      | ? (another bit flag? very rarely 1)                                                                                                                                                 |
| ...    |
| 40     | 1?      | ? (another bit flag? very rarely 0)                                                                                                                                                 |
| ...    |
| 45-47  | 1 each? | ? (more bit flags? sometimes 1)                                                                                                                                                     |
| 48     | 4?      | ?                                                                                                                                                                                   | 0x 00 03 01 00, 0x 02 00 00 00, 0x 00 03 00 00                                       |
| 52     | 4?      | ?                                                                                                                                                                                   | 0x 00 00 02 03                                                                       |
| ...    |
| 60     | 4       | Sample rate in Hz (float32)                                                                                                                                                         | 44100.0 (0x 00 44 2C 47)                                                             |
| 64     | 4       | ?                                                                                                                                                                                   | 0x 20 33 50 4D, 0x 20 41 34 4D                                                       |
| 68     | 4       | File type (not sure what this means)                                                                                                                                                | 0                                                                                    |
| 72     | 2       | File folder count (not sure what this means)                                                                                                                                        | 0, 5                                                                                 |
| 74     | 2       | Library folder count (not sure what this means)                                                                                                                                     | 0, 1                                                                                 |
| 76     | 2       | Number of artworks (you can attach more than one)                                                                                                                                   |
| 78     | 2       | ?                                                                                                                                                                                   | 51                                                                                   |
| 80     | 2?      | ? (might be signed, 0x ff ff is a common value along with 0)                                                                                                                        |
| 82     | 2?      | ?                                                                                                                                                                                   | 0, 1, 2                                                                              |
| 84     | 4       | Total size of all attached artworks (bytes)                                                                                                                                         | 234                                                                                  |
| 88     | 4       | Bit rate                                                                                                                                                                            |
| 92     | 4       | Date added                                                                                                                                                                          |
| ...    |
| 100    | 4       | ? (a bit flag? 0 or 1)                                                                                                                                                              |
| ...    |
| 108    | 4?      | ? (observed changing on first song play/skip)                                                                                                                                       | 0x 10 02 00 00 00, 0x 40 02 00 00 00, 0x 40 08 00 00, 0x A1 02 00 00, 0 (rare value) |
| 112    | 4?      | ? (observed changing on first song play/skip, values generally 500-3000 range, not unique)                                                                                          |
| ...    |
| 120    | 4?      | ? (observed changing on first song play/skip)                                                                                                                                       | 0, 1, 0x 03 00 00 02                                                                 |
| 124    | 4       | ? (custom lyrics tiny hash? 0 if no custom lyrics, otherwise, always the same value for the same custom lyrics, lyrics [only stored in audio file](#data-stored-in-the-audio-file)) |
| 128    | 4       | Date modified                                                                                                                                                                       |
| 132    | 4       | Normalization                                                                                                                                                                       |
| 136    | 4       | Purchase date                                                                                                                                                                       |
| 140    | 4       | Release date                                                                                                                                                                        |
| 144    | 4       | ?                                                                                                                                                                                   | 0, 2                                                                                 |
| 148    | 4       | ?                                                                                                                                                                                   | 0, 0x 61 34 70 6D                                                                    |
| 152    | 4       | ? (mostly 0, many values in the low 100s)                                                                                                                                           | 0, 0x 23 01 00 00                                                                    |
| 156    | 4       | Song duration in milliseconds                                                                                                                                                       |
| 160    | 4       | Album ID in Apple Music store (see [iama](#iama-album) offset 104)                                                                                                                  |
| ...    |
| 168    | 4       | Artist ID in Apple Music store (see [iAma](#iama-artist) offset 52)                                                                                                                 |
| ...    |
| 184    | 4       | ? (mostly 0, rarely 2)                                                                                                                                                              |
| ...    |
| 200    | 4       | ? (see [plma](#plma-library-master) offset 104)                                                                                                                                     |
| ...    |
| 208    | 4       | _Album_ Artist ID in Apple Music store (see [iAma](#iama-artist) offset 52)                                                                                                         |
| ...    |
| 256    | 4?      | ? (observed changing on first song play/skip, not unique)                                                                                                                           | 0, 0x AC A4 AE 00                                                                    |
| ...    |
| 264    | 4?      | ? (almost always 0, sometimes 16, 29, other values \< 100)                                                                                                                          |
| ...    |
| 272    | 4       | ? (an ID?)                                                                                                                                                                          |
| ...    |
| 280    | 4       | ? (see [plma](#plma-library-master) offset 104)                                                                                                                                     |
| ...    |
| 288    | 8?      | ?                                                                                                                                                                                   | 0, 0x 37 F8 94 37 4B F4 01 00                                                        |
| 296    | 4       | File size                                                                                                                                                                           |
| ...    |
| 304    | 4       | Song ID in Apple Music store - plug into the end of the URL "https://music.apple.com/song/..." as decimal - 0 if a custom album                                                     |
| ...    |
| 328    | 8       | ? (see [itma](#itma-track) offset 220)                                                                                                                                              |
| ...    |
| 356    | 4       | ? (a date)                                                                                                                                                                          |
| ...    |

I discovered that there can be 2 of the [track numerics](#track-numerics) section under the same [itma](#itma-track) after a purchased song is downloaded. However, _I think this is a bug_, because it seems to prepend an entire new one along with a bunch of other data, leaving the second (original) one nearly unchanged in the process (the [global counter](#global-counter) is still incremented through the extras, presumably because whatever code is maintaining this is not operating under the uniqueness assumption). I assume the extra ones then go undetected and unused, because the official program made no complaints after I removed them myself. Most conclusively, I decided to push the limits the other way by adding 100 duplicates of the subsection, then I changed some known data in the official program (specifically I changed offset 84 by adding more artworks), and only the first one got changed.

Grandparents: [itma](#itma-track)

Parents: [boma](#boma-binary-object) (subtype 0x1)

# Track Plays and Skips

[Back to TOC](#table-of-contents)

Seems completely understood: X

The length is always 52 bytes (the boma parent always has associated sections length 72).

| Offset | Length | Meaning                                                                                                                           | Examples Value(s) |
| ------ | ------ | --------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| 0      | 8      | Track ID                                                                                                                          |
| 8      | 4      | Last played date (0 for never, including if reset)                                                                                |
| 12     | 4      | Play count (can be reset in the GUI)                                                                                              |
| 16     | 4      | True play count (resetting in the GUI does not affect this count)                                                                 |
| 20     | 4      | First ever played date (in UTC time zone) (also not affected by GUI reset)                                                        |
| ...    |
| 28     | 4      | Last skipped date                                                                                                                 |
| 32     | 4      | Skip count                                                                                                                        |
| 36     | 4      | True skip count? (cannot find any way to reset the skip count in the GUI)                                                         |
| 40     | 4      | ? (by analogy with the play data, I speculate that this might become nonzero if you were able to reset the skip count in the GUI) |
| ...    |

Grandparents: [itma](#itma-track)

Parents: [boma](#boma-binary-object) (subtype 0x17)

# Video

[Back to TOC](#table-of-contents)

Seems completely understood: X

The length is always 52? (I don't have any of these in my library to check, but Gary Vollink's table ends at offset 48 (remember to subtract 20) with size 4 without a "..." after.)

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Vertical resolution   | 480               |
| 4      | 4      | Horizontal resolution | 640               |
| ...    |
| 48     | 4      | Framerate?            | 24                |

Grandparents: [itma](#itma-track)

Parents: [boma](#boma-binary-object) (subtype 0x24)

# lPma (Playlist List)

[Back to TOC](#table-of-contents)

Seems completely understood: ✓

"Apple Music playlist list"?

Appears only once.

| Offset | Length | Meaning               | Examples Value(s) |
| ------ | ------ | --------------------- | ----------------- |
| 0      | 4      | Section signature     | lPma              |
| 4      | 4      | Section length        | 92                |
| 8      | 4      | Number of subsections | 8                 |
| ...    |

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
- "Genius"

Playlist folders are implemented as special playlists, along with the parent folder pointer ID at offset 50. See [SLst (Smart Playlist Rules List)](#slst-smart-playlist-rules-list) and its subsection [playlists](#playlists) for more on this.

| Offset | Length | Meaning                                                                                                                      | Examples Value(s)  |
| ------ | ------ | ---------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| 0      | 4      | Section signature                                                                                                            | lpma               |
| 4      | 4      | Section length                                                                                                               | 368                |
| 8      | 4      | Associated sections length                                                                                                   | 1234               |
| 12     | 4      | Number of subsections                                                                                                        | 8                  |
| 16     | 4      | Number of tracks in playlist                                                                                                 | 10                 |
| ...    |
| 22     | 4      | Playlist creation date                                                                                                       | 3818534400         |
| 26     | 4      | See [Global Counter](#global-counter)                                                                                        |
| 30     | 8      | Playlist ID                                                                                                                  | 0x883E9012A290710E |
| 38     | 1? 4?  | ? (always 1)                                                                                                                 |
| ...    |
| 44     | 1? 2?  | ? (always 0 except for the "####!####" playlist, which has 1, might be a flag indicating this special "everything" playlist) |
| 46     | 1? 2?  | ? (always 0, except that it's 0x 00 01 on certain smart playlists (including folders))                                       |
| 48     | 1? 2?  | ? (same as 46 but a bigger set of smart playlists)                                                                           |
| 50     | 8      | Playlist ID of parent playlist folder (nothing to do with the [lPma](#lpma-playlist-list) section parent)                    |
| ...    |
| 78     | 2? 4?  | Special playlist ID                                                                                                          | see below          |
| ...    |
| 138    | 4      | Playlist modified date                                                                                                       | 3818534400         |
| ...    |
| 174    | 2? 4?  | ? (mostly 0, otherwise mostly values \<500, but some values as high as 36k)                                                  |
| 178    | 2? 4?  | ? (repeat of previous)                                                                                                       |
| 182    | 4      | ? (a date?)                                                                                                                  |
| 186    | 4?     | ? (mostly 0x 00 00 00 01, sometimes 0x 01 00 00 01)                                                                          |
| 192    | 4?     | ? (0, 6, or 46 in decreasing frequency)                                                                                      |
| ...    |
| 223    | 1      | Suggestion flag                                                                                                              | see below          |
| ...    |
| 263    | 16     | Artwork UUID in [artwork.sqlite](#artworksqlite), 0 if no artwork                                                            | 0xDDAE1C...        |
| ...    |
| 280    | 8      | ? (an ID?)                                                                                                                   |
| ...    |
| 296    | 4?     | ? (usually 102, sometimes 0, sometimes 60, observed changing when artwork changed)                                           |
| 300    | 4?     | ? (usually 8, sometimes 0, observed changing when artwork changed)                                                           |
| ...    |
| 316    | 4?     | ? (usually 1, sometimes 0, observed changing when artwork changed)                                                           |
| 320    | 4?     | ? (0, 1, or 2, observed changing when artwork changed)                                                                       |
| 324    | 4      | Suggestion flag modified date, 0 if never                                                                                    | 3818534400         |
| ...    |
| 356    | 4      | ? (almost always 2, otherwise maybe a date for 3 smart playlists in my library)                                              |
| ...    |

Changing the playlist's view options updates the modified date, even though the view options are stored in the [preferences folder](#preferences).

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
- 0xC9: [SLst (Smart Playlist Rules List)](#slst-smart-playlist-rules-list)
- [Strings](#string-section):
  - 0xC8 = playlist name (UTF-16)
- [Raw Strings](#raw-string)
  - 0xCD = "cover artwork recipe" plist (XML) (UTF-8) (describes how the artwork for a playlist was automatically generated (either from its name on a preset picture, or as a collage of 4 artworks from tracks))

# ipfa (Playlist Item)

[Back to TOC](#table-of-contents)

Seems completely understood: X

"Apple ? playlist item"?

One [lpma](#lpma-playlist) can have many ipfa grandchilldren. This is the only (known) [boma](#boma-binary-object) subtype where this is possible.

Another way this kind of section is unique is that the order they are saved in actually matters: it determines the playlist order of the songs.

| Offset | Length | Meaning                                                                                                                                                                                                                                                         | Examples Value(s) |
| ------ | ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- |
| 0      | 4      | Section signature                                                                                                                                                                                                                                               | ipfa              |
| 4      | 4      | Section length                                                                                                                                                                                                                                                  | 68                |
| 8      | 4      | See [Global Counter](#global-counter)                                                                                                                                                                                                                           |
| 12     | 8      | ipfa ID                                                                                                                                                                                                                                                         |
| 20     | 8      | Track ID                                                                                                                                                                                                                                                        |
| ...    |
| 40     | 2? 4?  | ? (nearly but not always unique, long streaks of values counting up by 1, 2, 3, etc. amid the chaos; may refer to [global counter](#global-counter), has been observed with higher values but only slightly and maybe haven't found the end of the counter yet) | 139, 1111         |
| 44     | 8      | ipfa ID again (if last track in playlist?)                                                                                                                                                                                                                      |
| ...    |

Grandparents: [lpma](#lpma-playlist)

Parents: [boma](#boma-binary-object) (subtype 0xCE)

# Smart Playlist Options

[Back to TOC](#table-of-contents)

Seems completely understood: X

The length is always 112 bytes (the boma parent always has associated sections length 132).

| Offset | Length | Meaning                                                                                 | Examples Value(s) |
| ------ | ------ | --------------------------------------------------------------------------------------- | ----------------- |
| 0      | 1      | Checkbox "live updating"                                                                |
| 1      | 1      | Checkbox to enable matching rules, keeps associated information even if unchecked       |
| 2      | 1      | Checkbox to enable limit                                                                |
| 3      | 1      | Limit unit                                                                              | see below         |
| 4      | 1      | Selection (ordering) method for limit                                                   | see below         |
| ...    |
| 8      | 4      | Limit count                                                                             |
| 12     | 1      | Checkbox "match only checked items" — see the notes about [itma](#itma-track) offset 42 |
| 13     | 1      | Negate ordering method, see below                                                       | 0, 1              |
| 14     | 1?     | ? (seems like a boolean flag, 0 except for the Genius playlist which has 1)             |
| ...    |
| 16     | 1?     | ?                                                                                       | 7 (a?)            |
| ...    |

The GUI enforces that either matching rules or the limit (offsets 1 and 2) must be enabled to save the smart playlist (otherwise it would just yield all songs).

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

Offset 13 is always 0 for the other offset 4 values (but I wonder if they could also be negated by setting the flag?).

Grandparents: [lpma](#lpma-playlist)

Parents: [boma](#boma-binary-object) (subtype 0xCA)

# SLst (Smart Playlist Rules List)

[Back to TOC](#table-of-contents)

"Smart playList"?

Seems completely understood: ✓

Length is always 136.

**_<h1>All numbers and strings in this section type and its descendants are big-endian!!</h1>_**

| Offset | Length | Meaning                                           | Examples Value(s) |
| ------ | ------ | ------------------------------------------------- | ----------------- |
| 0      | 4      | Section signature                                 | SLst              |
| 4      | 4?     | ? (_not the section length_)                      | 0x00010001 (a?)   |
| 8      | 4      | Number of subsections                             |
| 12     | 4      | Match \_\_\_ of the following rules (conjunction) | see below         |
| ...    |

Offset 15 conjunction enum values:

- 0 = all
- 1 = any

I refer to this as "conjunction", as in grammatical, not logical conjunction (which is "and", i.e. "all" in this case).

Grandparents: [lpma](#lpma-playlist)

Parents:

- [boma](#boma-binary-object) (subtype 0xC9)
- [Smart Playlist Rule](#smart-playlist-rule)

Children: [Smart Playlist Rule](#smart-playlist-rule)

(SLst and smart playlist rule may alternate being nested inside each other to an unlimited depth, so technically SLst can be its own grandparent as well.)

# Smart Playlist Rule

[Back to TOC](#table-of-contents)

Seems completely understood: [almost](#unknown-smart-playlist-field)

Length is always 56.

**_<h1>All numbers and strings in this section type and its descendants are big-endian!!</h1>_**

| Offset | Length | Meaning                                                                                    | Examples Value(s) |
| ------ | ------ | ------------------------------------------------------------------------------------------ | ----------------- |
| 0      | 4      | Subtype (field)                                                                            | see below         |
| 4      | 4      | Comparison method                                                                          | see below         |
| 8      | 4?     | ? (only nonzero for [nested smart playlist rules list](#nested-smart-playlist-rules-list)) | 0x 10 00 00 00    |
| ...    |
| 44     | 4      | ? (1 sometimes?)                                                                           |
| ...    |
| 52     | 4?     | Associated sections length _starting from offset 56_ (i.e. not including this section)     |

Unfortunately, no, offset 0 does not match the related boma subtype in all cases (though it does in some).

In all cases for offset 4, it looks like the bit 0x 02 00 00 00 is set to negate the comparison (but not all comparisons have a counterpart with this bit set available through the GUI, which makes me wonder if the program would accept these values).

Parents: [SLst](#slst-smart-playlist-rules-list)

Children:

- [SLst](#slst-smart-playlist-rules-list) (see [Nested Smart Playlist Rules List](#nested-smart-playlist-rules-list))
- Smart Playlist Rule Arguments, however as the contents of this section type depend so heavily on the contents of the parent smart playlist rule, they will be described below instead of in a separate section of this document
- [Raw strings](#raw-string): string argument in UTF-16 _big-endian!!_

When the child is smart playlist rule arguments, it looks like this:

It always has length 68.

| Offset | Length | Meaning                  | Examples Value(s) |
| ------ | ------ | ------------------------ | ----------------- |
| 0      | 8      | Argument 0               | default 1         |
| 8      | 8      | Argument 1               | default 0         |
| 16     | 8      | Argument 2               | default 1         |
| 24     | 8      | Argument 3               | default 1         |
| 32     | 8      | Argument 4? (never used) | default 0         |
| 40     | 8      | Argument 5? (never used) | default 1         |
| 48     | 8      | Argument 6? (never used) | default 0         |
| 56     | 8      | Argument 7? (never used) | default 0         |
| ...    |

- The fact that arguments 0, 2, 3, and 5 are by default terminated with a 0x01 byte, along with the actual way the arguments are filled into these arguments (0 and 3 are used most often), could also suggest that they are supposed to be arguments of size 8, 16, 8, 16, and 20 instead, however under this interpretation the one case where a 16-byte argument gets used ([Dates](#dates)), it is split in half anyway.
- Each argument is used for one parameter of the smart playlist rule (even if it isn't large enough to require all of its bytes)
- Unused arguments (those not mentioned as having a specific value below) are left with the default values above

## Nested Smart Playlist Rules List

Offset 0: 0x 00 00 00 00

Offset 4: 0x 00 00 00 01

Offset 8: 0x 01 00 00 00 (only nonzero for this section type)

Child: [SLst](#slst-smart-playlist-rules-list)

## Booleans

Offset 0 subtype (field) enum values:

- 0x 00 00 00 25 = "album artwork", i.e. has artwork (true) or not (false)
- 0x 00 00 00 1D = "checked" (referred to as "disabled" at [itma](#itma-track) offset 42; _just like there, this uses reversed values compared to other booleans_)
- 0x 00 00 00 1F = compilation
- 0x 00 00 00 29 = purchased

Offset 4 comparison method enum values:

- 0x 00 00 00 01 = is true
- 0x 02 00 00 01 = is false

Child: Smart Playlist Rule Arguments, but all not used (all default as described above)

## Numerics

Offset 0:

- 0x 00 00 00 5A = album (star) rating
- 0x 00 00 00 05 = bit rate in kbps
- 0x 00 00 00 23 = BPM
- 0x 00 00 00 18 = disc number
- 0x 00 00 00 A1 = movement number
- 0x 00 00 00 16 = plays
- 0x 00 00 00 19 = (star) rating (of track)
- 0x 00 00 00 06 = sample rate in Hz — given as integer at offset 56 (even though it's stored as a float in [track numerics](#track-numerics), so I can only assume "is" will never match those)
- 0x 00 00 00 1C = size in MB
- 0x 00 00 00 44 = skips
- 0x 00 00 00 0D = time (song duration) in milliseconds (GUI only allows you to enter with precision of seconds — would more precise values work?)
- 0x 00 00 00 0B = track number
- 0x 00 00 00 07 = year (of track)

Offset 4:

- 0x 00 00 00 01 = is
- 0x 02 00 00 01 = is not
- 0x 00 00 00 10 = is greater than
- 0x 00 00 00 40 = is less than
- 0x 00 00 01 00 = is in the range

Child: Smart Playlist Rule Arguments

- argument 0: first argument
- argument 3: second argument
  - it is always zero except for "is in the range", since this is the only comparison method with 2 arguments
- for star ratings, uses these values:
  - 0 stars = -20 (0x FF FF FF FF FF FF FF EC)
  - otherwise the usual 20 (0x 00 00 00 14) = 1 star up to 100 (0x 00 00 00 64) = 5 stars

## Dates

Offset 0:

- 0x 00 00 00 10 = date added
- 0x 00 00 00 0A = date modified
- 0x 00 00 00 17 = date last played
- 0x 00 00 00 45 = date last skipped

Offset 4:

- 0x 00 00 01 00 = is
- 0x 02 00 01 00 = is not
- 0x 00 00 00 10 = is after
- 0x 00 00 00 40 = is before
- 0x 00 00 02 00 = is in the last
- 0x 02 00 02 00 = is not in the last
- 0x 00 00 01 00 = is in the range (same as "is", the difference is in offset 56)

Child: Smart Playlist Rule Arguments

The official program only allows selecting with a precision of 1 day. (It also seems to handle time zones poorly — the date you select may have shifted by 1 when you open the rules again.)

- For "is" and "is not":
  - argument 0: midnight of the date chosen, e.g. 0x 00 00 00 00 E5 76 23 80 = 2025-12-28T00:00:00
  - argument 3: 23:59:59 of the same date, e.g. 0x 00 00 00 00 E5 77 74 FF = 2025-12-28T23:59:59
  - this suggests it is actually using numeric "is in the range" and "is not in the range" internally (is "is not in the range" a valid value for other numerics even though it's not presented in the GUI?)
  - would the official program accept more precise bounds edited in?
- For "is after":
  - argument 0 and argument 3 both set to 23:59:59 of the date chosen
  - seems to be using "is greater than"
- For "is before":
  - argument 0 and argument 3 both set to midnight of the date
  - seems to be using "is less than"
- For "is in the last" and "is not in the last":
  - argument 0 and argument 3 both filled in with 0x 2D AE repeated
    - not sure what the significance of this value is
    - I find it amusing that reading it aloud sounds a bit like "today", which might just be a coincidence
  - argument 1: the count, negated
    - for example, for "is in the last 1 \<unit\>", you get 0x FF FF FF FF FF FF FF FF (-1)
  - argument 2:
    - 0x 00 00 00 00 00 01 51 80 = 86,400 seconds = 1 day → unit is days
    - 0x 00 00 00 00 00 09 3a 80 = 604,800 seconds → weeks
    - 0x 00 00 00 00 00 28 19 A0 = 2,628,000 seconds = 86,400 \* 365 / 12 → months
  - this makes me wonder what would happen if you:
    - edited in a positive count
    - edited in some other unit
- For "is in the range":
  - argument 0: midnight of the first date chosen
  - argument 3: 23:59:59 of the second date chosen
  - if you select the same date for both bounds, close the rules list, and reopen it, the official program GUI will show it as an "is" rule, proving that there is literally no difference!

## Enums

Offset 0:

- Suggestion flags:
  - 0x 00 00 00 9C = album ("album favorite")
  - 0x 00 00 00 9A = track (just "favorite")
- 0x 00 00 00 86 = cloud status
- 0x 00 00 00 85 = location
- 0x 00 00 00 3C = media kind

Offset 4:

- 0x 00 00 00 01 = is
- 0x 02 00 00 01 = is not
- for location, does not use the above:
  - 0x 00 00 04 00 = is
  - 0x 02 00 04 00 = is not

Child: Smart Playlist Rule Arguments

- argument 0 and argument 3 are both set identically to the enum value argument
- Suggestion flags:
  - set to value as described under [itma](#itma-track) (value of 1 is not used)
- Cloud status:
  - 2 = matched
  - 1 = purchased (this is the order in the GUI — yes, it bothers me too that 1 is not first)
  - 3 = uploaded
  - 4 = ineligible
  - 5 = removed
  - 6 = error
  - 7 = duplicate
  - 8 = Apple Music
  - 9 = no longer available
  - 10 = not uploaded
- Location:
  - 1 = on computer
  - 16 = iCloud
- Media kind:
  - 0x 01 = music
  - 0x 20 = music video
  - 0x 02 = movies
  - 0x 40 = TV shows
  - 0x 05 = podcasts
  - 0x 08 = audio books
  - 0x 10 00 00 = voice memos
  - 0x 01 00 00 = iTunes extras
  - 0x 04 00 = home videos
  - seems to me like they couldn't decide if they wanted to use a specific bit for each value or not (podcasts has 2 bits set)

## Strings

Offset 0:

- 0x 00 00 00 03 = album
- 0x 00 00 00 47 = album artist
- 0x 00 00 00 04 = artist
- 0x 00 00 00 37 = category
- 0x 00 00 00 0E = comments
- 0x 00 00 00 12 = composer
- 0x 00 00 00 36 = description
- 0x 00 00 00 08 = genre
- 0x 00 00 00 27 = grouping
- 0x 00 00 00 09 = kind
- 0x 00 00 00 A0 = movement name
- 0x 00 00 00 4F = sort album
- 0x 00 00 00 51 = sort album artist
- 0x 00 00 00 50 = sort artist
- 0x 00 00 00 52 = sort composer
- 0x 00 00 00 53 = sort show
- 0x 00 00 00 4E = sort title
- 0x 00 00 00 02 = title
- 0x 00 00 00 59 = video rating
- 0x 00 00 00 9F = work name

Offset 4:

- 0x 01 00 00 02 = contains
- 0x 03 00 00 02 = does not contain
- 0x 01 00 00 01 = is (exact full match)
- 0x 03 00 00 01 = is not
- 0x 01 00 00 04 = begins with
- 0x 01 00 00 08 = ends with

Child: [Raw string](#raw-string) argument in UTF-16 _big-endian!!_

## Playlists

Playlist folders are actually implemented as a special kind of smart playlist. In fact, their binary data are nearly identical to smart playlists (including subsection data) with rules that look like:

- Match _any_ of the following rules:
  - Playlist is \<1st playlist in folder\>
  - Playlist is \<2nd playlist in folder\>
  - etc.

See below for the differences.

Offset 0: 0x 00 00 00 28

Offset 4:

- 0x 00 00 00 01 = is
- 0x 02 00 00 01 = is not

Child: Smart Playlist Rule Arguments

- argument 0: playlist ID _with bytes reversed compared to the usual order_ (matching how everything else is big-endian in here)
- argument 3: same playlist ID _only if this smart playlist is actually a playlist folder_, otherwise 0

## Unknown Smart Playlist Field

Offset 0: 0x 00 00 00 A4

Offset 4: 0x 00 00 00 01

Child: Smart Playlist Rule Arguments, all default

This only appears only inside of the "TV & Movies" special playlist, and there is no corresponding value inside of the GUI to put a name to it. From the rest of the data, I'm guessing it's a boolean.

# LPma (Padding?)

[Back to TOC](#table-of-contents)

"Apple Music library padding"?

Appears once at the end of my library in an hsma by itself. Hasn't always been present (not in a library from 3 months ago (September 2025)), but a newly-created library also has it (as of December 2025).

| Offset | Length | Meaning           | Examples Value(s) |
| ------ | ------ | ----------------- | ----------------- |
| 0      | 4      | Section signature | LPma              |
| 4      | 4      | Section length    | 96                |
| ...    |
| 12     | 1?     | ?                 | 6                 |
| ...    |

Parents: [hsma](#hsma-section-header)

# Accompanying Files

[Back to TOC](#table-of-contents)

Notably, I do not have any other .musicdb files as mentioned by Gary Vollink ("Application.musicdb" and "Library Preferences.musicdb"). I can only speculate that they have been replaced by some or all of the below (but here we are still stuck with "Library.musicdb", hence this project).

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

## .itdb Files

.itdb files are sqlite databases. There are 2:

One is Extras.itdb.

```
sqlite3 Extras.itdb
SQLite version...
Enter ".help" for usage hints.
sqlite> select * from sqlite_schema;
table|cddb|cddb|3|CREATE TABLE cddb (item_id INTEGER NOT NULL, media_id TEXT, mui_id TEXT, ufid TEXT, PRIMARY KEY (item_id))
table|uits|uits|4|CREATE TABLE uits (item_pid INTEGER NOT NULL, data TEXT, PRIMARY KEY (item_pid))
```

However, my Extras.itdb is empty, so I don't know what it's for. (It's getting its modification date bumped along with everything else, so it's not unused.)

The other is Genius.itdb, but it seems to encrypted so I have no idea what's in it. But given that I don't use Genius, I probably don't care about anything inside.

## Preferences

I'm guessing that the file Preferences.plist likely contains all top-level application settings, by which I mean:

- everything in the Settings menu
- which sidebar entries are shown
- show downloaded items only
- global equalizer
- playback shuffle on/off
- playback repeat off/one/all
- playback volume

At the very least changing them did not make any changes to the Library.musicdb file, other than modification dates (to the entire file and, for some reason, all playlists), with the following exceptions:

- The media folder location
  - see [plma](#plma-library-master) grandchildren [boma](#boma-binary-object) subtypes 0x1FD, 0x1F8, and 0x200
  - I'm guessing this is included in Library.musicdb because it affects locations of music files
- "Settings" → "General" → "Show" → "Songs list checkboxes"
  - see [plma](#plma-library-master) offset 24 and [itma](#itma-track) offset 42
  - I'm guessing this is included in Library.musicdb because it is related to data that is stored per-track (as opposed to other data that only affects playback)
- "Settings" → "Files" → "Keep media folder organized"
  - see [plma](#plma-library-master) offset 148
  - I'm guessing this is included in Library.musicdb because it affects locations of music files (they might be moved when this is enabled)

The folder "preferences" contains .plist files which seem to be the options for:

- Playlists: files are called "Playlist\_\<playlist ID\>.plist", e.g. "Playlist_4018ae797d0cea3c.plist" — note that the bytes have been reversed compared to the Library.musicdb file, so this one has 0x 3c ea 0c... in its lpma section.
- Albums: likewise "Album\_\<album ID\>.plist"
- Special built-in lists:
  - Albums.plist
  - Artists.plist
  - RecentlyAddedMusic.plist
  - Songs.plist
  - PlayQueueState.plist ("Playing Next"/"History" — not options, but the 2 lists of songs)

# Data Stored in the Audio File

[Back to TOC](#table-of-contents)

The official program understands [ID3 tags](https://id3.org/id3v2.3.0). Some data is stored only in the audio file:

- ID3 version
- lyrics
- more?

and some data is stored redundantly in both the Library.musicdb file and the audio file:

- comments
- more?
