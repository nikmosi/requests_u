from functools import wraps

from requests_u.general.Raiser import Raiser


def check_on_tag(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        Raiser.check_on_tag(res)
        return res

    return wrapper
