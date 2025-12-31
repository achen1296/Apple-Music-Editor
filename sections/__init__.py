from sections.shared_enums import StarRating, SuggestionFlag

from .album import StarRatingInheritance, bomaAlbum, iama, lama
from .artist import bomaArtist, iAma, lAma
from .binary_object import DataContainerSection, boma
from .header import hfma, hsma
from .library_master import bomaLibraryMaster, plma
from .playlist import (SLst, SmartPlaylistOptions, SpecialPlaylist,
                       bomaPlaylist, ipfa, lPma, lpma)
from .section import Section
from .smart_playlist_options import (LimitSelectionMethod,
                                     LimitSelectionMethodModifier, LimitUnit,
                                     SmartPlaylistOptions)
from .smart_playlist_rule import (BooleanComparison, BooleanField, CloudStatus,
                                  DateComparison, DateField, EnumComparison,
                                  EnumField, Location, MediaKind,
                                  NumericComparison, NumericField,
                                  PlaylistComparison, PlaylistField,
                                  SmartPlaylistRule,
                                  StarRatingSmartPlaylistArgument,
                                  StringComparison, StringField)
from .smart_playlist_rules_list import Conjunction, SLst, SmartPlaylistRule
from .track import (ContentRating, Downloaded, TrackNumerics, TrackPlaysSkips,
                    Video, bomaTrack, itma, ltma)

Data = boma

Boundary = hsma
SectionHeader = hsma

Envelope = hfma
FileHeader = hfma

LibraryMaster = plma

AlbumList = lama
Album = iama

AristList = lAma
Artist = iAma

TrackList = ltma
Track = itma

PlaylistList = lPma
Playlist = lpma
SmartPlaylistRules = SLst
