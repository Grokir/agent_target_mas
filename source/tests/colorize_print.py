
def red(message: str) -> str:
    return f"\033[31m{message}\033[0m"

def green(message: str) -> str:
    return f"\033[32m{message}\033[0m"

def blue(message: str) -> str:
    return f"\033[34m{message}\033[0m"

def cyan(message: str) -> str:
    return f"\033[36m{message}\033[0m"

def bold(message:str) -> str:
    return f"\033[1m{message}\033[0m"

def underline(message:str) -> str:
    return f"\033[4m{message}\033[0m"
