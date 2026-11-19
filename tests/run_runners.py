"""Runs several runners of the line protocol on one file of requests, for tests/crosscheck.cmake and
tests/api/pipeline.cmake.

    python3 tests/run_runners.py REQUESTS DIR NAME COMMAND [ARGS...] [-- NAME COMMAND [ARGS...]]...

Each runner reads REQUESTS on its standard input. Then, for each runner in order, one line on
standard output:

    NAME STATUS FIRST

STATUS is the runner's exit status, and FIRST the name of the first runner whose output is the same
as this one's, byte for byte (NAME itself if there is none before it). The output of each FIRST is
written to DIR/FIRST.txt, byte for byte; the output of a runner that failed is written too, and
compared with no other. A runner's standard error is passed on.

Python's standard library only. It runs the runners itself and reads their output through a pipe,
because writing it to a file as the runner goes was the slow part on the Windows machine of
docs/developer/testing.md: there cmake's execute_process with OUTPUT_FILE, or a file as the
scalar runner's standard output, cost 0.09 to 0.1 seconds per run on 2 000 requests, against 0.02
through a pipe; and cmake's OUTPUT_VARIABLE drops bytes (NUL, and the CR of CR LF) that a
byte-for-byte comparison must see.
"""
import hashlib
import os
import subprocess
import sys


def main(argv):
    if len(argv) < 4:
        sys.exit(__doc__)
    requests, out_dir, rest = argv[0], argv[1], argv[2:]
    runners, current = [], []
    for word in rest + ["--"]:
        if word == "--":
            if len(current) < 2:
                sys.exit("run_runners.py: each runner needs a name and a command")
            runners.append((current[0], current[1:]))
            current = []
        else:
            current.append(word)
    first_of = {}                    # SHA-256 of an output -> the name of its first runner
    lines = []
    for name, command in runners:
        with open(requests, "rb") as stdin:
            done = subprocess.run(command, stdin=stdin, stdout=subprocess.PIPE)
        first = name
        if done.returncode == 0:
            first = first_of.setdefault(hashlib.sha256(done.stdout).hexdigest(), name)
        if first == name:
            with open(os.path.join(out_dir, name + ".txt"), "wb") as f:
                f.write(done.stdout)
        lines.append("%s %d %s" % (name, done.returncode, first))
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
