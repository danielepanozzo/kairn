"""Kairn's generator: one description per kernel, printed as a Rocq model and as C++.

Modules, each meant to be read on its own:
    ir       the kernel IR, the description format, flattening
    expr     the parser of the rational expressions used by the claims
    rules    the checks every kernel passes before anything is printed
    rocq     the Rocq printer (trusted)
    cpp      the C++ printer (trusted)
    claims   gen/claims.json
    interp   the exact interpreter, a runner of the line protocol
    build    what build writes and check compares
"""
