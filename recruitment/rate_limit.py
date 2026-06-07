"""
Rate limiting simples baseado na cache do Django.
Uso: @rate_limit(rate='5/m') numa view function.
"""
from functools import wraps
from django.core.cache import cache
from django.http import HttpResponse


def rate_limit(rate='5/m', key='ip'):
    """
    Decorador de rate limiting por IP ou utilizador autenticado.

    rate: 'N/s', 'N/m' ou 'N/h'
    key:  'ip' (por endereço IP) ou 'user' (por utilizador autenticado)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            limit, timeout = _parse_rate(rate)
            if key == 'user' and request.user.is_authenticated:
                cache_key = f'rl:{view_func.__name__}:u:{request.user.pk}'
            else:
                cache_key = f'rl:{view_func.__name__}:ip:{_get_ip(request)}'

            count = cache.get(cache_key, 0)
            if count >= limit:
                return HttpResponse(
                    'Demasiados pedidos. Aguarde um momento e tente novamente.',
                    status=429,
                    content_type='text/plain; charset=utf-8',
                )
            cache.set(cache_key, count + 1, timeout=timeout)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator


def _parse_rate(rate):
    """Converte '5/m' para (5, 60)."""
    limit, period = rate.split('/')
    periods = {'s': 1, 'm': 60, 'h': 3600}
    return int(limit), periods.get(period, 60)


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')
