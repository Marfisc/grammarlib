import functools
from typing import Iterable, List, Dict, Set, Callable, Any, Optional, Union, Tuple, cast, overload
from dataclasses import dataclass


Expansion = Tuple["Symbol", ...]


class Symbol:
    def __mul__(self, other: Union["Symbol", "ExpansionAlternatives"]) -> "ExpansionAlternatives":
        if isinstance(other, Symbol):
            return ExpansionAlternatives([(self, other)])
        else:
            return ExpansionAlternatives([ (self, *expansion) for expansion in other.expansions ])

    def __or__(self, other: Union["Symbol", "ExpansionAlternatives"]) -> "ExpansionAlternatives":
        if isinstance(other, Symbol):
            return ExpansionAlternatives([(self,), (other,)])
        else:
            return ExpansionAlternatives([ (self,), *other.expansions ])


@dataclass(frozen=True)
class Terminal(Symbol):
    text: str

    def __str__(self):
        return '"' + self.text + '"'


@dataclass(frozen=True)
class ExpansionAlternatives:
    expansions: Iterable[Expansion]

    def __mul__(self, other: Union["Symbol", "ExpansionAlternatives"]) -> "ExpansionAlternatives":
        if isinstance(other, Symbol):
            return ExpansionAlternatives([ (*se, other) for se in self.expansions ])
        else:
            return ExpansionAlternatives([ (*se, *oe) for se in self.expansions for oe in other.expansions ])

    def __or__(self, other: Union["Symbol", "ExpansionAlternatives"]) -> "ExpansionAlternatives":
        if isinstance(other, Symbol):
            return ExpansionAlternatives([*self.expansions, (other,)])
        else:
            return ExpansionAlternatives([ *self.expansions, *other.expansions ])


def never() -> ExpansionAlternatives:
    return ExpansionAlternatives([])


def epsilon() -> ExpansionAlternatives:
    return ExpansionAlternatives([tuple()])


class NonTerminal(Symbol):
    label: str | None
    alternatives: ExpansionAlternatives

    def __init__(self, *, label: str | None, alternatives: ExpansionAlternatives):
        self.label = label
        self.alternatives = alternatives

    def __str__(self):
        return self.label or "unnamed"

    def __repr__(self):
        return f"NonTerminal(label={repr(self.label)})"

    def add_expansion(self, alternative: ExpansionAlternatives):
        self.alternatives = self.alternatives | alternative


class Grammar:
    starting_non_terminal: NonTerminal
    non_terminals: Set[NonTerminal]

    def __init__(self, starting_non_terminal):
        self.starting_non_terminal = starting_non_terminal
        self.non_terminals = set()
        self._add_non_terminal(starting_non_terminal)

    def _add_non_terminal(self, non_terminal: NonTerminal):
        if non_terminal in self.non_terminals:
            return
        self.non_terminals.add(non_terminal)
        for expansion in non_terminal.alternatives.expansions:
            for symbol in expansion:
                if isinstance(symbol, NonTerminal):
                    self._add_non_terminal(symbol)

    def first_sets(self) -> Dict[NonTerminal, Set[Optional[Terminal]]]:
        result: Dict[NonTerminal, Set[Optional[Terminal]]] = {}

        for non_terminal in self.non_terminals:
            result[non_terminal] = set()

        changed = True
        while changed:
            changed = False

            for non_terminal in self.non_terminals:
                for expansion in non_terminal.alternatives.expansions:
                    can_be_empty = True
                    for symbol in expansion:
                        first_set_of_symbol = set()
                        if isinstance(symbol, NonTerminal):
                            first_set_of_symbol = result[symbol]
                        elif isinstance(symbol, Terminal):
                            first_set_of_symbol = {symbol}

                        if not first_set_of_symbol.issubset(result[non_terminal]):
                            result[non_terminal] = result[non_terminal].union(first_set_of_symbol)
                            changed = True

                        if not (None in first_set_of_symbol):
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
                for expansion in non_terminal.alternatives.expansions:
                    current_follow_set = result[non_terminal]

                    for symbol in reversed(expansion):
                        if isinstance(symbol, Terminal):
                            current_follow_set = {symbol}
                        elif isinstance(symbol, NonTerminal):
                            if not current_follow_set.issubset(result[symbol]):
                                result[symbol] = result[symbol].union(current_follow_set)
                                changed = True
                            if None in first_sets[symbol]:
                                copy_of_first_set = set(first_sets[symbol])
                                copy_of_first_set.remove(None)
                                current_follow_set = current_follow_set.union(copy_of_first_set)
                            else:
                                current_follow_set = first_sets[symbol]

        return result

    def show(self) -> str:
        result: List[str] = []
        for non_terminal in self.non_terminals:
            for expansion in non_terminal.alternatives.expansions:
                result.append(str(non_terminal) + " <- " + " ".join((str(s) for s in expansion)) + "\n")
        return "".join(result)


@overload
def nt(label: str, expansions: Symbol | ExpansionAlternatives) -> NonTerminal: ...

@overload
def nt(expansions: Symbol | ExpansionAlternatives, /) -> NonTerminal: ...

def nt(label: str | Symbol | ExpansionAlternatives, expansions: Symbol | ExpansionAlternatives | None = None) -> NonTerminal:
    if isinstance(label, str) and expansions is not None:
        return NonTerminal(label = label, alternatives = epsilon() * expansions)
    elif not isinstance(label, str):
        return NonTerminal(label = None, alternatives = epsilon() * label)
    else:
        raise ValueError("nt: Provide either label and expansion or just expansion")


def parametric_nt[**P](f: Callable[P, NonTerminal]) -> Callable[P, NonTerminal]:
    @functools.wraps(f)
    def result(*args: P.args, **kwargs: P.kwargs) -> NonTerminal:
        inner_result = f(*args, **kwargs)
        if inner_result.label is None:
            inner_result.label = f.__name__
        inner_result.label += '(' + ', '.join(map(repr, args)) + ')'
        return inner_result
    return cast(Callable[P, NonTerminal], functools.cache(result))


def label_nts(variables: Dict[str, Any]) -> Dict[str, NonTerminal]:
    for k, v in variables.items():
        if isinstance(v, NonTerminal) and v.label is None:
            v.label = k
    return {}


def t(text: str):
    return Terminal(text)


def _main():
    @parametric_nt
    def pnt(x: int) -> NonTerminal:
        if x <= 0:
            return nt(t("a"))
        return nt(pnt(x - 1) * t("x"))

    ta = t("a")
    tb = t("b")
    a = nt(ta)
    b = nt("B", tb)
    d = nt((a | b) * (a | b))
    c = nt(a | a * b | d * tb | pnt(3))
    label_nts(vars())
    g = Grammar(c)
    print(g.show())
    for sym, follow_set in g.follow_sets().items():
        print(f"{sym} [{', '.join(map(str, follow_set))}]")


if __name__ == "__main__":
    _main()

