from flask import session, request
from sqlalchemy import text
from datetime import date, timedelta
from .forms import filter_activity_date_query


def set_activity_type_filters(filters, key):
    if not filters or not key:
        return True

    at_filter = True
    if request.method == 'POST':
        if filters.activity_types.data:
            at_filter = text('activity.activity_type_id=%d' % filters.activity_types.data.id)
            session[key] = filters.activity_types.data.id
        else:
            session.pop(key, None)
    else:
        if key in session:
            at_filter = text('activity.activity_type_id=%d' % session[key])
            from .models import ActivityType
            filters.activity_types.data = ActivityType.get_by_id(session[key])
    return at_filter


def set_status_filters(filters, key):
    if not filters or not key:
        return True

    status_filter = True
    if request.method == 'POST':
        if filters.status_filter.data:
            status_val = filters.status_filter.data
            if status_val == 'pending':
                # pending means NOT completed, NOT cancelled, NOT overdue
                status_filter = text("activity.status='pending' AND "
                                     "(activity.scheduled_date >= current_timestamp)")
            elif status_val == 'overdue':
                status_filter = text("activity.status='pending' AND "
                                     "(activity.scheduled_date < current_timestamp)")
            else:
                status_filter = text("activity.status='%s'" % status_val)
            session[key] = status_val
        else:
            session.pop(key, None)
    else:
        if key in session:
            status_val = session[key]
            if status_val == 'pending':
                status_filter = text("activity.status='pending' AND "
                                     "(activity.scheduled_date >= current_timestamp)")
            elif status_val == 'overdue':
                status_filter = text("activity.status='pending' AND "
                                     "(activity.scheduled_date < current_timestamp)")
            else:
                status_filter = text("activity.status='%s'" % status_val)
            filters.status_filter.data = status_val
    return status_filter


def set_date_adv_filters(f_id, module):
    today = date.today()
    filter_d = True
    if f_id == 1:
        # Today
        filter_d = text("scheduled_date "
                        "BETWEEN date_trunc('day', current_timestamp) AND "
                        "date_trunc('day', current_timestamp) + "
                        "interval '1 day' - interval '1 second'")
    elif f_id == 2:
        # Next 7 days
        filter_d = text("scheduled_date "
                        "BETWEEN date_trunc('day', current_timestamp) AND "
                        "date_trunc('day', current_timestamp) + interval '7 day' - interval '1 second'")
    elif f_id == 3:
        # Next 30 days
        filter_d = text("scheduled_date "
                        "BETWEEN date_trunc('day', current_timestamp) AND "
                        "date_trunc('day', current_timestamp) + interval '30 day' - interval '1 second'")
    elif f_id == 4:
        # Overdue
        filter_d = text("activity.status='pending' AND scheduled_date < current_timestamp")
    elif f_id == 5:
        # Created today
        filter_d = text("date(%s.date_created)='%s'" % (module, today))
    elif f_id == 6:
        # Created in last 7 days
        filter_d = text("date(%s.date_created) > current_date - interval '7' day" % module)
    return filter_d


def set_date_filters(filters, module, key):
    filter_d = True
    if request.method == 'POST':
        if filters.advanced_filter.data:
            filter_d = set_date_adv_filters(filters.advanced_filter.data['id'], module)
            session[key] = filters.advanced_filter.data['id']
        else:
            session.pop(key, None)
    else:
        if key in session:
            filter_d = set_date_adv_filters(session[key], module)
            filters.advanced_filter.data = filter_activity_date_query()[session[key] - 1]
    return filter_d
