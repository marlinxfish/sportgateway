from .models import OperationalHour, DAYS_OF_WEEK

def create_default_operational_hours(field):
    for day, _ in DAYS_OF_WEEK:
        OperationalHour.objects.create(
            field=field,
            day=day,
            open_time='08:00',
            close_time='17:00',
            is_closed=False
        )
