import sys
from nuitka.__main__ import main

my_opts = [
    "--standalone",
    "--mingw64",
    "--python-flag=nosite",
    "--remove-output",
    "--experimental=use_pefile",
    "--disable-dll-dependency-cache",
]

new_sysargs = [sys.argv[0]]
for o in my_opts:
    new_sysargs.append(o)

new_sysargs.extend(sys.argv[1:])

sys.argv = new_sysargs
print("Invoking NUITKA with these options:")
for o in sys.argv[1:]:
    print(" " + o)
print(" ")

main()
