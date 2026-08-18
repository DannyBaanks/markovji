#!/usr/bin/env python3
"""
Kaomoji Markov — Markov algorithm esolang with kaomoji syntax.

:     = unary atom (only data unit)
:P    = program entry point
:O    = wildcard (matches any run of :)
:3    = rule separator (LHS :3 RHS)
xD    = rule terminator
:) :( :D :] :[ ;) = variables $0..$5 (bind greedily to :+)
jajaja = comment (ignored)

Execution: scan rules in order, apply first matching rule, restart scan.
Halt when no rule matches.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
from pathlib import Path


@dataclass
class Rule:
    lhs: Pattern
    rhs: Pattern
    var_count: int
    emit: Optional[str] = None


@dataclass
class Pattern:
    """Sequence of atoms: ':', ':O', or variable refs."""
    elements: List[str]  # each: ':' | ':O' | '$0'..'$5'

    def match(self, tape: str, pos: int = 0) -> Optional[Tuple[int, Dict[str, str]]]:
        """Try to match pattern at tape[pos:]. Returns (end_pos, bindings) or None."""
        bindings = {}
        p = pos
        for elem in self.elements:
            if elem == ':':
                if p >= len(tape) or tape[p] != ':':
                    return None
                p += 1
            elif elem == ':O':
                # Wildcard: match one or more ':' greedily, bind to $O
                start = p
                while p < len(tape) and tape[p] == ':':
                    p += 1
                if p == start:  # must match at least one
                    return None
                bindings['$O'] = tape[start:p]
            elif elem.startswith('$'):
                # Variable: if already bound, match exact bound value; else bind greedily
                var_name = elem
                if var_name in bindings:
                    # Match exact bound value
                    bound_val = bindings[var_name]
                    if tape[p:p+len(bound_val)] != bound_val:
                        return None
                    p += len(bound_val)
                else:
                    # Bind greedily (one or more ':')
                    start = p
                    while p < len(tape) and tape[p] == ':':
                        p += 1
                    if p == start:
                        return None
                    bindings[var_name] = tape[start:p]
            else:
                return None
        return p, bindings

    def substitute(self, bindings: Dict[str, str]) -> str:
        """Expand pattern with variable bindings."""
        out = []
        for elem in self.elements:
            if elem == ':':
                out.append(':')
            elif elem == ':O':
                out.append(bindings.get('$O', ':'))
            elif elem == '~':
                out.append('~')  # emit marker
            elif elem.startswith('$'):
                out.append(bindings.get(elem, ''))
            else:
                out.append(elem)
        return ''.join(out)

    def __str__(self):
        return ''.join(self.elements)


class KaomojiMarkov:
    VAR_MAP = {
        ':)': '$0', ':(': '$1', ':D': '$2',
        ':]': '$3', ':[': '$4', ';)': '$5'
    }
    REVERSE_VAR_MAP = {v: k for k, v in VAR_MAP.items()}

    def __init__(self, source: str):
        self.rules: List[Rule] = []
        self.tape = ""
        self.output: List[str] = []
        self._parse(source)

    def _parse(self, source: str) -> None:
        lines = source.splitlines()
        mode = "start"
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            if ln.startswith('jajaja'):
                continue
            if mode == "start":
                if ln == ':P':
                    mode = "rules"
                    continue
                else:
                    raise ValueError("Program must start with :P")
            elif mode == "rules":
                if ln == '::=':
                    mode = "base"
                    continue
                self._parse_rule(ln)
            elif mode == "base":
                self.tape = self._decode_tape(ln)
                break

    def _parse_rule(self, line: str) -> None:
        # Split by :3 and xD
        if ':3' not in line or 'xD' not in line:
            raise ValueError(f"Invalid rule (missing :3 or xD): {line}")
        
        lhs_str, rest = line.split(':3', 1)
        rhs_str, _ = rest.split('xD', 1)
        
        lhs_str = lhs_str.strip()
        rhs_str = rhs_str.strip()
        
# Handle emit prefix ~ (like jajaja: ~text emits text, ~ alone emits newline)
        emit = None
        if rhs_str.startswith('~'):
            emit = rhs_str[1:] if len(rhs_str) > 1 else '\n'
            rhs_str = ''  # RHS pattern is empty for emit rules
        
        lhs = self._parse_pattern(lhs_str)
        rhs = self._parse_pattern(rhs_str) if rhs_str else Pattern([])
        
        # Count max variable index used
        var_indices = set()
        for elem in lhs.elements + rhs.elements:
            if elem.startswith('$'):
                var_indices.add(int(elem[1:]))
        var_count = max(var_indices) + 1 if var_indices else 0
        
        self.rules.append(Rule(lhs, rhs, var_count, emit))

    def _parse_pattern(self, s: str) -> Pattern:
        elements = []
        i = 0
        while i < len(s):
            if s[i] == ':':
                # Check for multi-char kaomoji
                if i + 1 < len(s):
                    two = s[i:i+2]
                    if two in self.VAR_MAP:
                        elements.append(self.VAR_MAP[two])
                        i += 2
                        continue
                    elif two == ':O':
                        elements.append(':O')
                        i += 2
                        continue
                    elif two == ':P':
                        elements.append(':')  # :P in pattern = just :
                        i += 2
                        continue
                # Single :
                elements.append(':')
                i += 1
            elif s[i] == '~':
                # Emit marker
                elements.append('~')
                i += 1
            else:
                # Skip unknown (shouldn't happen with valid input)
                i += 1
        return Pattern(elements)

    def _decode_tape(self, s: str) -> str:
        """Convert kaomoji tape to internal : representation."""
        out = []
        i = 0
        while i < len(s):
            if s[i] == ':':
                if i + 1 < len(s):
                    two = s[i:i+2]
                    if two in self.VAR_MAP or two in (':O', ':P', ':3'):
                        # These don't appear in tape normally, treat as :
                        out.append(':')
                        i += 2
                        continue
                out.append(':')
                i += 1
            else:
                i += 1
        return ''.join(out)

    def step(self) -> bool:
        for rule in self.rules:
            match = rule.lhs.match(self.tape)
            if match:
                end_pos, bindings = match
                
                # Handle emit rule
                if rule.emit is not None:
                    # Substitute variables in emit text ($0, $1, $O, etc.)
                    emitted = rule.emit
                    for var, val in bindings.items():
                        emitted = emitted.replace(var, val)
                    self.output.append(emitted)
                    self.tape = self.tape[end_pos:]
                else:
                    # Normal replacement
                    rhs_expanded = rule.rhs.substitute(bindings)
                    self.tape = self.tape[:0] + rhs_expanded + self.tape[end_pos:]
                return True
        return False

    def step_debug(self) -> bool:
        """Debug step showing what happened."""
        for i, rule in enumerate(self.rules):
            match = rule.lhs.match(self.tape)
            if match:
                end_pos, bindings = match
                matched = self.tape[:end_pos]
                rhs_expanded = rule.rhs.substitute(bindings)
                print(f"  Rule {i}: matched '{matched}' -> '{rhs_expanded}'")
                self.tape = self.tape[:0] + rhs_expanded + self.tape[end_pos:]
                return True
        return False

    def run(self, max_steps: int = 100000) -> Tuple[str, int, str]:
        self.output = []
        steps = 0
        while steps < max_steps:
            if not self.step():
                return "".join(self.output), steps, "HALTED"
            steps += 1
        return "".join(self.output), steps, "MAX_STEPS"


def run(source: str, max_steps: int = 100000) -> Tuple[str, int, str]:
    try:
        return KaomojiMarkov(source).run(max_steps=max_steps)
    except Exception as e:
        return "", 0, f"ERROR: {e}"


def run_file(path: Path, max_steps: int = 100000) -> Tuple[str, int, str]:
    return run(path.read_text(encoding='utf-8'), max_steps)


def main():
    import sys
    if len(sys.argv) > 1:
        output, steps, status = run_file(Path(sys.argv[1]))
        print(f"[{status}] pasos={steps}")
        if output:
            print(f"Salida: {output}")
    else:
        demo = """:P
:O :3 ~::::: xD
::=
:"""
        output, steps, status = run(demo)
        print(f"Demo: hola mundo")
        print(f"[{status}] pasos={steps}")
        print(f"Salida: {output}")


if __name__ == "__main__":
    main()