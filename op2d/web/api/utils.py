
from sipsimple.configuration import DefaultValue

__all__ = ['get_state', 'set_state']


def get_state(obj):
    def cleanup_state(o, old_state):
        state = {}
        for k, v in old_state.iteritems():
            if v is DefaultValue:
                v = getattr(o, k)
            elif isinstance(v, dict):
                v = cleanup_state(getattr(o, k), v)
            if hasattr(v, '__getstate__'):
                v = v.__getstate__()
            if v in ('true', 'false'):
                # fix booleans to be real booleans and not strings
                v = True if v=='true' else False
            state[k] = v
        return state
    return cleanup_state(obj, obj.__getstate__())


def set_state(obj, state):
    valid_keys = dir(obj.__class__)
    for k, v in ((k, v) for k, v in state.iteritems() if k in valid_keys):
        if isinstance(v, dict):
            o = getattr(obj, k, None)
            if o is not None:
                set_state(o, v)
        else:
            setattr(obj, k, v)

