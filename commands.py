import sys

def echo(sender: str, args: str) -> str:
    """Repeats whatever text the user provides."""
    return args if args else "(nothing to echo)"

def hello(sender: str, args: str) -> str:
    """Responds with a greeting."""
    return f"Hi, {sender}!"

def help(sender: str, args: str) -> str:
    """Prints this message"""
    response_lines = ["Available commands:"]
    current_module = sys.modules[__name__]
    for name in dir(current_module):
        func = getattr(current_module, name)
        if callable(func) and not name.startswith("__"):
            doc = func.__doc__ or "(no description)"
            response_lines.append(f"/{name} - {doc}")
    return "\n".join(response_lines)

def ping(sender: str, args: str) -> str:
    """Responds with 'Pong!'."""
    return "Pong!"
