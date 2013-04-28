"""
smokesignal.py - simple event signaling
"""
import sys

from collections import defaultdict
from functools import partial, wraps


__all__ = ['emit', 'signals', 'responds_to', 'on', 'once',
           'disconnect', 'disconnect_from', 'clear', 'clear_all']


# Collection of receivers/callbacks
_receivers = defaultdict(set)
_pyversion = sys.version_info[:2]


def emit(signal, *args, **kwargs):
    """
    Emits a single signal to call callbacks registered to respond to that signal.
    Optionally accepts args and kwargs that are passed directly to callbacks.

    :param signal: Signal to send
    """
    for callback in _receivers[signal]:
        callback(*args, **kwargs)


def signals(callback):
    """
    Returns a tuple of all signals for a particular callback

    :param callback: A callable registered with smokesignal
    :returns: Tuple of all signals callback responds to
    """
    return tuple(s for s in _receivers if responds_to(callback, s))


def responds_to(callback, signal):
    """
    Returns bool if callback will respond to a particular signal

    :param callback: A callable registered with smokesignal
    :param signal: A signal to check if callback responds
    :returns: True if callback responds to signal, False otherwise
    """
    for fn in _receivers[signal]:
        if callback in (fn, getattr(fn, '__wrapped__', None)):
            return True
    return False


def on(signals, callback=None, max_calls=None):
    """
    Registers a single callback for receiving an event (or event list). Optionally,
    can specify a maximum number of times the callback should receive a signal. This
    method works as both a function and a decorator::

        smokesignal.on('foo', my_callback)

        @smokesignal.on('foo')
        def my_callback():
            pass

    :param signals: A single signal or list/tuple of signals that callback should respond to
    :param callback: A callable that should repond to supplied signal(s)
    :param max_calls: Integer maximum calls for callback. None for no limit.
    """
    if isinstance(callback, int) or callback is None:
        # Decorated
        if isinstance(callback, int):
            # Here the args were passed arg-style, not kwarg-style
            callback, max_calls = max_calls, callback
        return partial(_on, signals, max_calls=max_calls)
    else:
        # Function call
        return _on(signals, callback, max_calls=max_calls)


def _on(signals, callback, max_calls=None):
    """
    Proxy for `smokesignal.on`, which is compatible as both a function call and
    a decorator. This method cannot be used as a decorator

    :param signals: A single signal or list/tuple of signals that callback should respond to
    :param callback: A callable that should repond to supplied signal(s)
    :param max_calls: Integer maximum calls for callback. None for no limit.
    """
    assert callable(callback), 'Signal callbacks must be callable'

    # Support for lists of signals
    if not isinstance(signals, (list, tuple)):
        signals = [signals]

    callback._max_calls = max_calls

    # Create a wrapper so we can ensure we limit number of calls
    @wraps(callback)
    def wrapper(*args, **kwargs):
        if callback._max_calls is None or callback._max_calls > 0:
            if callback._max_calls is not None:
                callback._max_calls -= 1
            return callback(*args, **kwargs)

    # Compatibility - Python >= 3.2 does this for us
    if _pyversion < (3, 2):
        wrapper.__wrapped__ = callback

    for signal in signals:
        _receivers[signal].add(wrapper)

    return wrapper


def once(signals, callback=None):
    """
    Registers a callback that will respond to an event at most one time

    :param signals: A single signal or list/tuple of signals that callback should respond to
    :param callback: A callable that should repond to supplied signal(s)
    """
    return on(signals, callback, max_calls=1)


def disconnect(callback):
    """
    Removes a callback from all signal registries and prevents it from responding
    to any emitted signal.

    :param callback: A callable registered with smokesignal
    """
    # XXX: This is inefficient. Callbacks should be aware of their signals
    disconnect_from(callback, signals(callback))


def disconnect_from(callback, signals):
    """
    Removes a callback from specified signal registries and prevents it from responding
    to any emitted signal.

    :param callback: A callable registered with smokesignal
    :param signals: A single signal or list/tuple of signals
    """
    # Support for lists of signals
    if not isinstance(signals, (list, tuple)):
        signals = [signals]

    # XXX: This is pretty inefficient and I should be able to quickly remove
    # something without checking the entire receiver list
    for signal in signals:
        for check in _receivers[signal].copy():
            if check == callback:
                _receivers[signal].remove(callback)
            elif callback == getattr(check, '__wrapped__', None):
                _receivers[signal].remove(check)


def clear(*signals):
    """
    Clears all callbacks for a particular signal or signals
    """
    for signal in signals:
        _receivers[signal].clear()


def clear_all():
    """
    Clears all callbacks for all signals
    """
    for key in _receivers.keys():
        _receivers[key].clear()
