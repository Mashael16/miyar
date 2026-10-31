# this file is a custom file where you define the Access Control rules for your API. It acts as a security layer that determines who can perform which actions beyond just being logged in.

from rest_framework.permissions import BasePermission, SAFE_METHODS

# self: Refers to the current permission class instance (e.g., IsManager).
#request: Contains the user's data (who is asking?) and the action (what are they doing?).
#view: Tells you which specific page or action (like create or delete) they are trying to reach.
from rest_framework import permissions

class IsManager(BasePermission):
    """
    Only managers can create/update/delete.
    Any authenticated user can read.
    """

    def has_permission(self, request, view):

        # Must be logged in first
        if not request.user or not request.user.is_authenticated:
            return False

        # Allow read-only methods
        if request.method in SAFE_METHODS:
            return True

        # Allow write only for managers
        return request.user.role == "manager"
    
class IsEmployee(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == "employee"
        )

class IsOwner(BasePermission):

    def has_object_permission(self, request, view, obj):
        return obj.assigned_to == request.user


class IsEvaluationOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role =="manager":
            return True
        return obj.task.assigned_to == request.user