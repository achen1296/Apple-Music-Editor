from typing import Callable, Iterable, Type

from library_musicdb import Library, Section, boma, hsma, plma


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

        self.children = self.subsections
        self.children_of_type = self.subsection_of_type

    def subsections(self):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                for sub in s.subsections:
                    yield sub

        self.search_actions.append(f)
        return self

    def subsection_of_type(self, type: Type[Section]):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            for s in sections:
                for sub in s.subsections:
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

    def parents_of_type(self, type: Type[Section]):
        def f(sections: Iterable[Section]) -> Iterable[Section]:
            seen_parents: set[Section] = set()

            for s in sections:
                if s.parent not in seen_parents:
                    if isinstance(s.parent, type):
                        yield s.parent
                    seen_parents.add(s.parent)

        self.search_actions.append(f)
        return self

    def search(self, *sections: Section):
        sections: Iterable[Section]
        for f in self.search_actions:
            sections = f(sections)
        return sections


if __name__ == "__main__":
    l = Library()
    ls = (
        LibrarySearcher()
        .subsection_of_type(hsma)
        .subsection_of_type(plma)
        .parents()
    )
    print(list(ls.search(l)))
