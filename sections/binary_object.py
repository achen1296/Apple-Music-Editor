from collections import defaultdict
from typing import override

from .section import Section


class String(Section):
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "signature": 0,
        "string_size": 4,
        "string": 16,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.signature == b"\x02\x00\x00\x00":
            self.encoding = "utf_8"
        elif self.signature == b"\x01\x00\x00\x00":
            self.encoding = "utf_16_le"
        else:
            raise ValueError(f"unexpected signature for a string {self.signature}, don't know what encoding to use")

    def get_string(self):
        return self._data[self.offsets["string"]:].decode(self.encoding)

    def set_string(self, value: str):
        self._edit_change_size()
        self._data[self.offsets["string"]:] = value.encode(self.encoding)
        self.set_int("string_size", self.size - self.offsets["string"])


class RawString(Section):
    offsets = {
        # no **Section.offsets: does not have a typical size offset
        "string": 0,
    }
    encoding = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_string(self):
        return self._data.decode(self.encoding)

    def set_string(self, value: str):
        self._edit_change_size()
        self._data = value.encode(self.encoding)


class RawStringUTF8(RawString):
    encoding = "utf_8"


class RawStringUTF16(RawString):
    encoding = "utf_16_le"


AnyString = String | RawString


class boma(Section):
    expected_signature = b"boma"
    offsets = {
        **Section.offsets,
        "total_size": 8,
        "subtype": 12,
    }
    # subsection_class_by_subtype to be set in subclasses unique to each parent

    @override
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subtype = self.get_int("subtype")  # convenient to have this


class DataContainerSection(Section):
    """ Add methods for boma subsections """

    data_subtypes: dict[str, int] = {}
    """ Subtype name -> subtype number """
    numeric_data_offsets: dict[int, dict[str, int]] = {}
    """ Subtype number -> offset name -> offset. Anything not given offsets here is assumed to be a string container. """
    numeric_data_sizes: defaultdict[int, defaultdict[str, int]] = defaultdict(lambda: defaultdict(lambda: 4))
    """ Subtype number -> offset name -> size. Anything not given offsets here is assumed to be a string container. """

    def data_subsection_of_subtype(self, subtype: str | int):
        if isinstance(subtype, str):
            subtype = self.data_subtypes[subtype]
        for s in self.subsections:
            if isinstance(s, boma) and s.subtype == subtype:
                return s  # assumes there's only one subsection with the specified subtype
        raise KeyError(self, subtype)

    def get_data_subsection_string(self, subtype: str | int):
        if isinstance(subtype, str):
            # if subtype given as int we will assume caller already knows what they're doing (or intentionally wants to bypass these checks e.g. for a section type unknown to the code)
            subtype_number = self.data_subtypes[subtype]
            if subtype_number in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a string")
        return self.data_subsection_of_subtype(subtype).get_string()

    def set_data_subsection_string(self, subtype: str | int, value: str):
        if isinstance(subtype, str):
            subtype_number = self.data_subtypes[subtype]
            if subtype_number in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a string")
        self.data_subsection_of_subtype(subtype).set_string(value)

    def get_data_subsection_int(self, subtype: str | int, key: str | tuple[int, int]):
        if isinstance(subtype, str):
            subtype_number = self.data_subtypes[subtype]
            if subtype_number not in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a numeric container")
            subtype = subtype_number
        if isinstance(key, str):
            key = (
                self.numeric_data_offsets[subtype][key],
                self.numeric_data_sizes[subtype][key]
            )
        return self.data_subsection_of_subtype(subtype).get_int(key)

    def set_data_subsection_int(self, subtype: str | int, key: str | tuple[int, int], value: int):
        if isinstance(subtype, str):
            subtype_number = self.data_subtypes[subtype]
            if subtype_number not in self.numeric_data_offsets:
                raise ValueError(f"subtype {subtype} is not supposed to be a numeric container")
            subtype = subtype_number
        if isinstance(key, str):
            key = (
                self.numeric_data_offsets[subtype][key],
                self.numeric_data_sizes[subtype][key]
            )
        self.data_subsection_of_subtype(subtype).set_int(key, value)

    @override
    def as_dict(self):
        d = super().as_dict()
        for subsection in self.subsections:
            if isinstance(subsection, boma):
                for subtype_name, subtype_number in self.data_subtypes.items():
                    if subtype_number == subsection.subtype:
                        if subtype_number in self.numeric_data_offsets:
                            d[subtype_name] = {
                                offset_name: subsection.get_int((offset, self.numeric_data_sizes[subtype_number][offset_name]))
                                for offset_name, offset in self.numeric_data_offsets[subtype_number].items()
                            }
                        else:
                            d[subtype_name] = subsection.get_string()
        return d

# don't know where these boma subtypes go because they aren't in my library
# listed as "book" type on vollink but not present in my library: 0x42,
# "unknown 64x4b hex string": 0x1f4,
# another "unknown 64x4b hex string": 0x1fe,
# "xml block (unknown utility)": 0x2bc,
# "xml block (unknown utility)": 0x3cc,
