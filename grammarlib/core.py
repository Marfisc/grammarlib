from typing import List, Dict, Set, Callable, Any, Optional, Union, Type
from dataclasses import dataclass


Terminal = str
TermList = List[Union["NonTerminal", "Capture", Terminal]]


@dataclass
class Production:
    terms: TermList


@dataclass
class Capture:
    non_termnial: "NonTerminal"
    variable: str


class NonTerminal:

    def __init__(self, func: Optional[Callable[["NonTerminal"], Any]] = None, *, label: Optional[str] = None):
        # if func is None and label is None:
        #    raise ValueError("Cannot leave out func and label")

        self.func: Optional[Callable[["NonTerminal"], Any]] = func
        self.label: Optional[str]  = label
        self.productions: List[Production] = []
        self.built: bool = False

        if self.label is None:
            if hasattr(func, "__name__"):
                self.label = func.__name__ #type: ignore

    def __call__(self, func: Callable[["NonTerminal"], Any]):
        if self.func is not None:
            raise ValueError("Func is already set")
        self.func = func

        if self.label is None:
            if hasattr(func, "func_name"):
                self.label = func.func_name #type: ignore
        return self

    def __repr__(self):
        if self.label is not None:
            return f"NonTerminal(label={repr(self.label)})"

    def build(self):
        if self.built:
            return
        if self.func is None:
            raise ValueError("NonTerminal missing function to create productions")
        self.built = True
        self.func(self)

    def add_production(self, *terms: Union[str, "NonTerminal", "Capture", Terminal]):
        self.productions.append(Production(list(terms)))


class Grammar:
    starting_non_terminal: NonTerminal
    non_terminals: Set[NonTerminal]

    def __init__(self, starting_non_terminal):
        self.starting_non_terminal = starting_non_terminal
        self.non_terminals = set()
        self._add_non_terminal(starting_non_terminal)

    def _add_non_terminal(self, non_termnial: NonTerminal):
        if non_termnial in self.non_terminals:
            return
        self.non_terminals.add(non_termnial)
        non_termnial.build()
        for production in non_termnial.productions:
            for term in production.terms:
                if isinstance(term, NonTerminal):
                    self._add_non_terminal(term)

    def first_sets(self) -> Dict[NonTerminal, Set[Optional[Terminal]]]:
        result: Dict[NonTerminal, Set[Optional[Terminal]]] = {}

        for non_terminal in self.non_terminals:
            result[non_terminal] = set()

        changed = True
        while changed:
            changed = False

            for non_terminal in self.non_terminals:
                for production in non_terminal.productions:
                    can_be_empty = True
                    for term in production.terms:
                        first_set_of_term = set()
                        if isinstance(term, NonTerminal):
                            first_set_of_term = result[term]
                        elif isinstance(term, Terminal):
                            first_set_of_term = {term}

                        if not first_set_of_term.issubset(result[non_terminal]):
                            result[non_terminal] = result[non_terminal].union(first_set_of_term)
                            changed = True

                        if not (None in first_set_of_term):
                            can_be_empty = False
                            break

                    if can_be_empty and not (None in result[non_terminal]):
                        result[non_terminal].add(None)
                        changed = True

        return result

    def follow_sets(self) -> Dict[NonTerminal, Set[Optional[Terminal]]]:
        result: Dict[NonTerminal, Set[Optional[Terminal]]] = {}
        for non_terminal in self.non_terminals:
            result[non_terminal] = set()
        result[self.starting_non_terminal].add(None)

        first_sets = self.first_sets()

        changed = True
        while changed:
            changed = False

            for non_terminal in self.non_terminals:
                for production in non_terminal.productions:
                    current_follow_set = result[non_terminal]

                    for term in reversed(production.terms):
                        if isinstance(term, Terminal):
                            current_follow_set = {term}
                        elif isinstance(term, NonTerminal):
                            if not current_follow_set.issubset(result[term]):
                                result[term] = result[term].union(current_follow_set)
                                changed = True
                            if None in first_sets[term]:
                                copy_of_first_set = set(first_sets[term])
                                copy_of_first_set.remove(None)
                                current_follow_set = current_follow_set.union(copy_of_first_set)
                            else:
                                current_follow_set = first_sets[term]

        return result


def _main():
    @NonTerminal
    def f(nt):
        nt.add_production("abc")
        nt.add_production(q, "def")
        nt.add_production(q, q, "def")
        nt.add_production(q, "following")

        print(repr(nt.productions))
        pass

    @NonTerminal(label="qqq")
    def q(nt):
        nt.add_production("qux")
        nt.add_production()
        pass

    print(f.label)
    print(q.label)


if __name__ == "__main__":
    _main()

