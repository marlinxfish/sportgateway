from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Field

def manager_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'role') or request.user.role != 'manager':
            messages.error(request, 'Anda tidak memiliki izin untuk mengakses halaman ini.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def field_owner_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, pk, *args, **kwargs):
        field = get_object_or_404(Field, pk=pk)
        if field.owner != request.user:
            messages.error(request, 'Anda tidak memiliki izin untuk mengakses halaman ini.')
            return redirect('fields:manager_field_list')
        return view_func(request, pk, *args, **kwargs)
    return _wrapped_view
