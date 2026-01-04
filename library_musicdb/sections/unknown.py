from .section import Section


# see readme
class LPma(Section):
    expected_signature = b"LPma"
    offsets = {
        **Section.offsets,
    }
