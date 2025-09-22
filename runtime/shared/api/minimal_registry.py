"""
Minimal Zero-Overhead Model Registry 
"""
_REGISTERED_MODELS = {}


def api_model(cls=None, *, name=None, tags=None, req_res=None):
    """
    minimal Decorator vor Model-registartion
    """

    def decorator(model_cls):
        model_name = name or model_cls.__name__

        _REGISTERED_MODELS[model_name] = {
            'class': model_cls,
            'module': model_cls.__module__,
            'tags': tags or set(),
            'req_res': req_res,
        }
        return model_cls

    if cls is not None:
        return decorator(cls)
    return decorator


# DevTools-Interface (build time)
def get_registered_models():
    """ get all models with decorators"""
    return _REGISTERED_MODELS.copy()


def get_models_by_req_res(req_res_type):
    return {name: info.copy() for name, info in _REGISTERED_MODELS.items() if info.get('req_res') == req_res_type}


def get_response_models():
    return get_models_by_req_res("response")


# Convenience-Aliases (zero-overhead)


def generic_model(cls=None, **kwargs):
    """generic Model - zero runtime overhead"""
    kwargs.setdefault('tags', {'generic'})
    return api_model(cls, **kwargs)


def owner_model(cls=None, **kwargs):
    """Owner-only Model - zero runtime overhead"""
    kwargs.setdefault('tags', {'owner'})
    return api_model(cls, **kwargs)
