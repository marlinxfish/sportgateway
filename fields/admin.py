from django.contrib import admin
from .models import Field, OperationalHour

@admin.register(Field)
class FieldAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'category', 'price_per_hour', 'created_at')
    search_fields = ('name', 'owner__username', 'category')

@admin.register(OperationalHour)
class OperationalHourAdmin(admin.ModelAdmin):
    list_display = ('field', 'day', 'open_time', 'close_time', 'is_closed')
    list_filter = ('field', 'day', 'is_closed')
