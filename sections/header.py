from .album import lama
from .artist import lAma
from .library_master import plma
from .playlist import lPma
from .section import Section
from .track import ltma
from .unknown import LPma


class hfma(Section):  # inner hfma only, not outer hfma which is Library
    expected_signature = b"hfma"
    offsets = {
        **Section.offsets,
        # some more known data listed here in vollink but none interesting to edit
    }


class hsma(Section):
    expected_signature = b"hsma"
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subtype": 12,
    }
    subsection_class_by_subtype = {
        3: hfma,
        6: plma,
        4: lama,
        5: lAma,
        1: ltma,
        2: lPma,
        17: LPma,
    }
