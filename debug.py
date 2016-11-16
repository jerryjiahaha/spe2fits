#!/usr/bin/env python3

from functools import wraps

# TODO Need test on generator
def debug_method_info(level = -1):
    # level is useless yet
    def decorator(func):
        @wraps(func)
        def method(*args, **kwargs):
            print(func, args, kwargs)
            return func(*args, **kwargs)
        return method
    return decorator
