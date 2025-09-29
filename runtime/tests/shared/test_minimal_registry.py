import pytest
from shared.minimal_registry import (api_model, generic_model, owner_model, get_registered_models, get_models_by_req_res, get_response_models, get_request_models,
                                     get_union_requests)


# Dummy models for registration
def test_api_model_registration():
    """Test that @api_model registers a class correctly."""

    @api_model
    class Foo:
        pass

    models = get_registered_models()
    assert 'Foo' in models
    assert models['Foo']['class'] is Foo


def test_api_model_with_options():
    """Test @api_model with custom name, tags, and req_res options."""

    @api_model(name="BarModel", tags={"x"}, req_res="response")
    class Bar:
        pass

    models = get_registered_models()
    assert 'BarModel' in models
    assert models['BarModel']['tags'] == {"x"}
    assert models['BarModel']['req_res'] == "response"


def test_generic_model_and_owner_model():
    """Test that @generic_model and @owner_model register classes with correct tags."""

    @generic_model
    class Gen:
        pass

    @owner_model
    class Own:
        pass

    models = get_registered_models()
    assert 'Gen' in models
    assert 'generic' in models['Gen']['tags']
    assert 'Own' in models
    assert 'owner' in models['Own']['tags']


def test_get_models_by_req_res():
    """Test that get_request_models and get_response_models return correct models."""

    @api_model(name="ReqModel", req_res="request")
    class Req:
        pass

    @api_model(name="ResModel", req_res="response")
    class Res:
        pass

    reqs = get_request_models()
    ress = get_response_models()
    assert 'ReqModel' in reqs
    assert 'ResModel' in ress


def test_union_request_detection():
    """Test that get_union_requests detects union models with discriminator fields."""
    from typing import Union

    class A:
        pass

    class B:
        pass

    @api_model(discriminator_field="kind")
    class UnionModel:
        model_fields = {'foo': type('Field', (), {'annotation': Union[A, B], 'discriminator': 'kind'})()}

    unions = get_union_requests()
    assert 'UnionModel' in unions
    assert unions['UnionModel']['discriminator_field'] == 'kind'
