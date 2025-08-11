class TerminalColors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def blue(val_or_string) -> str:
    return TerminalColors.OKBLUE + str(val_or_string) + TerminalColors.ENDC

def red(val_or_string) -> str:
    return TerminalColors.FAIL + str(val_or_string) + TerminalColors.ENDC

def bold(val_or_string) -> str:
    return TerminalColors.BOLD + str(val_or_string) + TerminalColors.ENDC
