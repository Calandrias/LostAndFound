# owner_handler_abc.py
"""Auto-generated abstract base class for Owner tag handlers."""

from abc import ABC, abstractmethod

# pylint: disable=unnecessary-pass # pass is okay for abstract class
class OwnerHandlerABC(ABC):
    """Abstract base class for Owner tag handlers."""
    # Each method corresponds to an API endpoint defined in the OpenAPI spec.
    # Decorators for Session Token handling and Method/Path validation adde based on API spec.

    @abstractmethod
    def owner_delete_account(self, event, context, cache):
        """Delete owner account (challenge/confirm) (DELETE /v1/owner)"""
        # Implement logic for owner_delete_account in derived class
        pass

    @abstractmethod
    def owner_get(self, event, context, cache):
        """Get owner account info/status (GET /v1/owner)"""
        # Implement logic for owner_get in derived class
        pass

    @abstractmethod
    def owner_login(self, event, context, cache):
        """Owner Auth (Challenge/Response) (POST /v1/owner/login)"""
        # Implement logic for owner_login in derived class
        pass

    @abstractmethod
    def owner_logout(self, event, context, cache):
        """Invalidate session token (logout) (POST /v1/owner/logout)"""
        # Implement logic for owner_logout in derived class
        pass

    @abstractmethod
    def owner_onboarding(self, event, context, cache):
        """Owner Registration / Onboarding (POST /v1/owner/onboarding)"""
        # Implement logic for owner_onboarding in derived class
        pass

    @abstractmethod
    def owner_session_refresh(self, event, context, cache):
        """Refresh a session token (POST /v1/owner/refresh)"""
        # Implement logic for owner_session_refresh in derived class
        pass

    @abstractmethod
    def owner_storage_delete(self, event, context, cache):
        """Delete owner private storage (challenge/confirm) (DELETE /v1/owner/storage)"""
        # Implement logic for owner_storage_delete in derived class
        pass

    @abstractmethod
    def owner_storage_get(self, event, context, cache):
        """Retrieve encrypted private data storage (GET /v1/owner/storage)"""
        # Implement logic for owner_storage_get in derived class
        pass

    @abstractmethod
    def owner_storage(self, event, context, cache):
        """Store or retrieve encrypted private data storage (POST /v1/owner/storage)"""
        # Implement logic for owner_storage in derived class
        pass

