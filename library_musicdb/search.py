import re
from typing import Callable, Iterable, Type

from .library import *
from .sections import Section
from .sections.binary_object import BinaryObjectParentSection, StringBase


class LibrarySearcher:
    """ Intended to be used with method chaining. `search` ends the chain by returning the actual results of the search instead of `self`. (You can use the same instance to `search` multiple times.) """

    def __init__(self):
        # list of functions that transform an Iterable of sections that have matched so far into a new Iterable that matches the next part of the search
        self.search_actions: list[
            Callable[
                [Iterable[Section]],
                Iterable[Section]
            ]
        ] = []

    def custom_predicate(self, predicate: Callable[[Section], bool]):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if predicate(s):
                    yield s

        self.search_actions.append(f)
        return self

    def discard(self, count: int):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for i, s in enumerate(sections):
                if i >= count:
                    yield s

        self.search_actions.append(f)
        return self

    def limit(self, count: int):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for i, s in enumerate(sections):
                if i < count:
                    yield s
                else:
                    break

        self.search_actions.append(f)
        return self

    def search(self, *sections: Section):
        sections: Iterable[Section]
        for f in self.search_actions:
            sections = f(sections)
        return sections

    # type and positional

    def of_type[T: Section](self, type: Type[T]):
        def f(sections: Iterable[Section]) -> Iterable[T]:
            for s in sections:
                if isinstance(s, type):
                    yield s

        self.search_actions.append(f)
        return self

    def subsections(self):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                for sub in s.subsections:
                    yield sub

        self.search_actions.append(f)
        return self

    children = subsections

    def subsections_of_type[T: Section](self, type: Type[T]):
        def f(sections: Iterable[Section]) -> Iterable[T]:
            for s in sections:
                for sub in s.subsections:
                    if isinstance(sub, type):
                        yield sub

        self.search_actions.append(f)
        return self

    children_of_type = subsections_of_type

    def descendants(self):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                for sub in s:
                    yield sub

        self.search_actions.append(f)
        return self

    def descendants_of_type[T: Section](self, type: Type[T]):
        def f(sections: Iterable[Section]) -> Iterable[T]:
            for s in sections:
                for sub in s:
                    if isinstance(sub, type):
                        yield sub

        self.search_actions.append(f)
        return self

    def parents(self):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            seen_parents: set[Section] = set()  # unlike children, can reach the same Section multiple ways

            for s in sections:
                if s.parent not in seen_parents:
                    yield s.parent
                    seen_parents.add(s.parent)

        self.search_actions.append(f)
        return self

    def parents_of_type[T: Section](self, type: Type[T]):
        def f(sections: Iterable[Section]) -> Iterable[T]:
            seen_parents: set[Section] = set()

            for s in sections:
                if s.parent not in seen_parents:
                    if isinstance(s.parent, type):
                        yield s.parent
                    seen_parents.add(s.parent)

        self.search_actions.append(f)
        return self

    def ancestors(self):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            seen_ancestors: set[Section] = set()

            for s in sections:
                while (
                    s.parent is not s
                    and s.parent not in seen_ancestors
                ):
                    yield s.parent
                    seen_ancestors.add(s.parent)
                    s = s.parent

        self.search_actions.append(f)
        return self

    def ancestors_of_type[T: Section](self, type: Type[T]):
        def f(sections: Iterable[Section]) -> Iterable[T]:
            seen_ancestors: set[Section] = set()

            for s in sections:
                while (
                    s.parent is not s
                    and s.parent not in seen_ancestors
                ):
                    if isinstance(s.parent, type):
                        yield s.parent
                    seen_ancestors.add(s.parent)
                    s = s.parent

        self.search_actions.append(f)
        return self

    # content

    def match_bytes(self, offset: str | int, value: bytes):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if s.get_bytes(offset, len(value)) == value:
                    yield s

        self.search_actions.append(f)
        return self

    def match_int(self, key: str | tuple[int, int], value: int):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if s.get_int(key) == value:
                    yield s

        self.search_actions.append(f)
        return self

    def match_string(self, pattern: str, *, case_sensitive=False):
        if not case_sensitive:
            pattern = pattern.lower()

        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if isinstance(s, StringBase):
                    string = s.get_string()
                    if not case_sensitive:
                        string = string.lower()
                    if pattern in string:
                        yield s

        self.search_actions.append(f)
        return self

    def re_match_string(self, pattern: str | re.Pattern, *, re_flags=re.I):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if isinstance(s, StringBase):
                    string = s.get_string()
                    if re.search(pattern, string, re_flags):
                        yield s

        self.search_actions.append(f)
        return self

    # data subsection content

    def data_subsections_of_subtype(self, subtype: str | int):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if isinstance(s, BinaryObjectParentSection):
                    yield s.data_subsection_of_subtype(subtype)

        self.search_actions.append(f)
        return self

    def match_sub_int(self, subtype: str | int, key: str | tuple[int, int], value: int):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if isinstance(s, BinaryObjectParentSection) and s.get_sub_int(subtype, key) == value:
                    yield s

        self.search_actions.append(f)
        return self

    def match_sub_string(self, subtype: str | int, pattern: str, *, case_sensitive=False):
        if not case_sensitive:
            pattern = pattern.lower()

        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if isinstance(s, BinaryObjectParentSection):
                    string = s.get_sub_string(subtype)
                    if not case_sensitive:
                        string = string.lower()
                    if pattern in string:
                        yield s

        self.search_actions.append(f)
        return self

    def re_match_sub_string(self, subtype: str | int, pattern: str | re.Pattern, *, re_flags=re.I):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if isinstance(s, BinaryObjectParentSection):
                    string = s.get_sub_string(subtype)
                    if re.search(pattern, string, re_flags):
                        yield s

        self.search_actions.append(f)
        return self
