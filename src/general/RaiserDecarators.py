from functools import wraps

import general.Raiser as Raiser


def check_on_tag(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        Raiser.check_on_tag(res)
        return res

    return wrapper
