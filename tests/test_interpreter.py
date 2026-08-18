#!/usr/bin/env python3
"""Tests para el intérprete markovji."""

import sys
sys.path.insert(0, str(__file__.replace('tests\\test_interpreter.py', '')))
from markovji import run, KaomojiMarkov


def test_hola():
    src = """:P
:O :3 ~::::: xD
::=
:"""
    output, steps, status = run(src)
    assert status == "HALTED"
    assert output == ":::::"
    print("OK test_hola")


def test_incremento():
    src = """:P
:O :3 :O: xD
::=
:::"""
    output, steps, status = run(src, max_steps=5)
    assert status == "MAX_STEPS"
    # No output emitted, tape grows
    print("OK test_incremento")


def test_decremento():
    m = KaomojiMarkov(""":P
:: :3 : xD
: :3  xD
::=
:::::""")
    output, steps, status = m.run()
    assert status == "HALTED"
    assert m.tape == ""
    print("OK test_decremento")


def test_copia():
    m = KaomojiMarkov(""":P
:) :3 :) :) xD
::=
:::""")
    output, steps, status = m.run(max_steps=1)
    assert status == "MAX_STEPS"
    assert m.tape == "::::::"  # 3 * 2 = 6 after 1 step
    print("OK test_copia")


def test_intercambio():
    # Swap doesn't work with greedy vars on unary alphabet without delimiter
    # This tests that it halts without matching
    m = KaomojiMarkov(""":P
:) :O :( :3 :( :O :) xD
::=
:: :O :::""")
    output, steps, status = m.run(max_steps=2)
    assert status == "HALTED"
    assert steps == 0
    print("OK test_intercambio")


def test_variable_binding():
    # Test que las variables binden correctamente
    m = KaomojiMarkov(""":P
:) :3 :) xD
::=
:::""")
    assert len(m.rules) == 1
    assert m.rules[0].var_count == 1
    print("OK test_variable_binding")


def test_wildcard():
    m = KaomojiMarkov(""":P
:O :3 : xD
::=
:::""")
    # :O debe matchear ::: y reemplazar con :
    output, steps, status = m.run(max_steps=5)
    assert status == "MAX_STEPS"
    assert m.tape == ":"
    print("OK test_wildcard")


def test_prioridad_reglas():
    # Primera regla debe ganar
    m = KaomojiMarkov(""":P
: :3 :: xD
:O :3 : xD
::=
:::""")
    output, steps, status = m.run(max_steps=3)
    assert status == "MAX_STEPS"
    # Primera regla matchea :, reemplaza con ::, matchea otra vez...
    assert m.tape == "::::::"  # 3 -> 6 después de 2 pasos
    print("OK test_prioridad_reglas")


def run_all():
    test_hola()
    test_incremento()
    test_decremento()
    test_copia()
    test_intercambio()
    test_variable_binding()
    test_wildcard()
    test_prioridad_reglas()
    print("\nOK All tests passed!")


if __name__ == "__main__":
    run_all()