from typing import List, Dict, Set, Callable, Any, Optional, Union, Type, Tuple
from dataclasses import dataclass


Production = Tuple["Symbol", ...]


class Symbol:
    def __mul__(self, other: Union["Symbol", "ProductionList"]) -> "ProductionList":
        if isinstance(other, Symbol):
            return ProductionList([(self, other)])
        else:
            return ProductionList([ (self, *production) for production in other.productions ])

    def __or__(self, other: Union["Symbol", "ProductionList"]) -> "ProductionList":
        if isinstance(other, Symbol):
            return ProductionList([(self,), (other,)])
        else:
            return ProductionList([ (self,), *other.productions ])


@dataclass(frozen=True)
class Terminal(Symbol):
    text: str

    def __str__(self):
        return '"' + self.text + '"'



@dataclass(frozen=True)
class ProductionList:
    productions: List[Production]

    def add(self, production: Production):
        self.productions.append(production)

    def __mul__(self, other: Union["Symbol", "ProductionList"]) -> "ProductionList":
        if isinstance(other, Symbol):
            return ProductionList([ (*sp, other) for sp in self.productions ])
        else:
            return ProductionList([ (*sp, *op) for sp in self.productions for op in other.productions ])

    def __or__(self, other: Union["Symbol", "ProductionList"]) -> "ProductionList":
        if isinstance(other, Symbol):
            return ProductionList([*self.productions, (other,)])
        else:
            return ProductionList([ *self.productions, *other.productions ])


class NonTerminal(Symbol):
    label: str
    production_list: ProductionList

    def __init__(self, *, label: str, production_list: ProductionList):
        self.label = label
        self.production_list = production_list

    def __str__(self):
        return "<" + self.label + ">"

    def __repr__(self):
        if self.label is not None:
            return f"NonTerminal(label={repr(self.label)})"

    def add_production(self, production: Production):
        self.production_list.add(production)


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
        for production in non_terminal.production_list.productions:
            for term in production:
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
                for production in non_terminal.production_list.productions:
                    can_be_empty = True
                    for term in production:
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
                for production in non_terminal.production_list.productions:
                    current_follow_set = result[non_terminal]

                    for term in reversed(production):
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

    def show(self) -> str:
        result: List[str] = []
        for non_terminal in self.non_terminals:
            for production in non_terminal.production_list.productions:
                result.append(str(non_terminal) + " <- " + " ".join((str(s) for s in production)) + "\n")
        return "".join(result)


def nt(label: str, productions: Optional[Union[Symbol, ProductionList]] = None):
    if isinstance(productions, Symbol):
        return NonTerminal(label = label, production_list = ProductionList([(productions,)]))
    return NonTerminal(label = label, production_list = productions or ProductionList([]))


def _main():
    ta = Terminal("a")
    tb = Terminal("b")
    a = nt("A", ta)
    b = nt("B", tb)
    d = nt("D", (a | b) * (a | b))
    c = nt("C", a | a * b | d * tb)
    g = Grammar(c)
    print(g.show())
    print(g.follow_sets())


if __name__ == "__main__":
    _main()

