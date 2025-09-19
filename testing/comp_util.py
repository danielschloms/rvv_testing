VERBOSE = False

def print_info(msg: str):
    if VERBOSE:
        print(msg)

def match_length(a: list, b: list, value) -> None:
    diff = abs(len(a) - len(b))
    if len(a) > len(b):
        b.extend([value] * diff)
    elif len(a) < len(b):
        a.extend([value] * diff)