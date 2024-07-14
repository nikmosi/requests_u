from requests_u.domain.exceptions.base import BaseDomainError


def test_base_domain_error_message():
    error = BaseDomainError()
    assert error.message == "Occur exception in domain"
