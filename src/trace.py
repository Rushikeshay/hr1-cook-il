"""Print how a ledger number was built, all the way back to its sources.

    python src/trace.py mcd_loss_2027_mid
    python src/trace.py --list            # all ids
    python src/trace.py --list snap_      # ids starting with snap_
"""
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from lib.ledger import load  # noqa: E402


def show(led, id, depth=0, seen=None):
    seen = seen if seen is not None else set()
    pad = "    " * depth
    if id not in led.index:
        print(f"{pad}{id}  ?? not in ledger")
        return
    r = led.loc[id]
    v = r.value
    val = f"{v:,.4f}" if abs(v) < 10 else f"{v:,.0f}"
    print(f"{pad}{id} = {val} {r.unit}  [{r.label}, {r.step}]")
    if r.formula:
        print(f"{pad}    = {r.formula}")
    if r.source:
        print(f"{pad}    source: {r.source}")
    if id in seen:
        return
    seen.add(id)
    for inp in filter(None, str(r.inputs).split(";")):
        show(led, inp, depth + 1, seen)


if __name__ == "__main__":
    led = load().set_index("id")
    if len(sys.argv) < 2:
        print(__doc__)
    elif sys.argv[1] == "--list":
        prefix = sys.argv[2] if len(sys.argv) > 2 else ""
        for id in sorted(i for i in led.index if i.startswith(prefix)):
            print(id)
    else:
        for id in sys.argv[1:]:
            show(led, id)
            print()
