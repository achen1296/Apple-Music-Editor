import re
from typing import Callable, Iterable, Type

from library_musicdb import *


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

    # generic content

    def match_bytes(self, offset: str | int, value: bytes):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if s.get_bytes(offset, len(value)) == value:
                    yield s

        self.search_actions.append(f)
        return

    def match_int(self, offset: str | int, value: int):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if s.get_int(offset) == value:
                    yield s

        self.search_actions.append(f)
        return

    def match_boma_str(self, pattern: str, *, case_sensitive=False):
        if not case_sensitive:
            pattern = pattern.lower()

        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if isinstance(s, boma):
                    string = s.get_string()
                    if not case_sensitive:
                        string = string.lower()
                    if pattern in string:
                        yield s

        self.search_actions.append(f)
        return self

    def re_match_boma_str(self, pattern: str | re.Pattern, *, re_flags=re.I):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                if isinstance(s, boma):
                    string = s.get_string()
                    if re.search(pattern, string, re_flags):
                        yield s

        self.search_actions.append(f)
        return self

    # shortcuts for data specific to known types

    def match_boma_subtype(self, boma_subtype: int):
        self.of_type(boma)
        self.match_int("boma_subtype", boma_subtype)
        return self

    def track_title(self, title: str | re.Pattern, *, re=False, **kwargs):
        self.descendants_of_type(itma)
        self.subsections_of_type(boma)
        self.match_boma_subtype(boma.subtypes["track_title"])
        if re:
            self.re_match_boma_str(title, **kwargs)
        else:
            self.match_boma_str(title, **kwargs)
        return self


if __name__ == "__main__":
    l = Library()
    ls = (
        LibrarySearcher()
        .track_title(input("track title: "))
        .parents()
        .children_of_type(boma)
        .match_boma_subtype(boma.subtypes["track_plays_and_skips"])
    )
    for s in ls.search(l):
        print(s)
        s.set_int(32, int(input("play count: ")))
    l.save()
