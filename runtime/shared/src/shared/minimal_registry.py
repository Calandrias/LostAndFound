""" Minimal Zero-Overhead Model Registry"""
from typing import Union

_REGISTERED_MODELS = {}


def api_model(cls=None, *, name=None, tags=None, req_res=None, discriminator_field=None):
    """
    Minimal decorator for model registration, with optional discriminator info.
    """

    def decorator(model_cls):
        model_name = name or model_cls.__name__
        # Try to auto-detect union/discriminator
        is_union_request = False
        detected_discriminator = None
        if hasattr(model_cls, 'model_fields'):
            for _field_name, field in model_cls.model_fields.items():
                ann = getattr(field, 'annotation', None)
                # Check for Union type
                if hasattr(ann, '__origin__') and ann is not None and ann.__origin__ is Union:
                    is_union_request = True
                    # Try to get discriminator from Field
                    detected_discriminator = getattr(field, 'discriminator', None) or discriminator_field
        _REGISTERED_MODELS[model_name] = {
            'class': model_cls,
            'module': model_cls.__module__,
            'tags': tags or set(),
            'req_res': req_res,
            'is_union_request': is_union_request,
            'discriminator_field': detected_discriminator,
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


def get_request_models():
    return get_models_by_req_res("request")


def get_union_requests():
    """Return all registered models that are union requests with a discriminator."""
    return {name: info.copy() for name, info in _REGISTERED_MODELS.items() if info.get('is_union_request') and info.get('discriminator_field')}


# Convenience-Aliases (zero-overhead)


def generic_model(cls=None, **kwargs):
    """generic Model - zero runtime overhead"""
    kwargs.setdefault('tags', {'generic'})
    return api_model(cls, **kwargs)


def owner_model(cls=None, **kwargs):
    """Owner-only Model - zero runtime overhead"""
    kwargs.setdefault('tags', {'owner'})
    return api_model(cls, **kwargs)
