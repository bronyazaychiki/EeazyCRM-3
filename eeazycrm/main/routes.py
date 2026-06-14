from flask import render_template, flash, url_for, redirect, Blueprint, current_app
from eeazycrm import db
from flask_login import login_required, current_user
from configparser import ConfigParser
from datetime import datetime, timedelta

parser = ConfigParser()

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
@login_required
def home():
    from eeazycrm.activities.models import Activity, ActivityStatus

    # Build base query - non-admin users only see their own activities
    base_q = Activity.query
    if not current_user.is_admin:
        base_q = base_q.filter(Activity.owner_id == current_user.id)

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_end = today_start + timedelta(days=7)

    # Overdue: pending activities with scheduled_date in the past
    overdue = base_q.filter(
        Activity.status == ActivityStatus.PENDING,
        Activity.scheduled_date < now
    ).order_by(Activity.scheduled_date.asc()).limit(5).all()

    # Today: pending activities scheduled today
    today_activities = base_q.filter(
        Activity.status == ActivityStatus.PENDING,
        Activity.scheduled_date >= today_start,
        Activity.scheduled_date < today_end
    ).order_by(Activity.scheduled_date.asc()).all()

    # Upcoming: pending activities in next 7 days (excluding today)
    upcoming = base_q.filter(
        Activity.status == ActivityStatus.PENDING,
        Activity.scheduled_date >= today_end,
        Activity.scheduled_date <= week_end
    ).order_by(Activity.scheduled_date.asc()).limit(5).all()

    return render_template("index.html", title="Dashboard",
                           overdue=overdue,
                           today_activities=today_activities,
                           upcoming=upcoming)


@main.route("/create_db")
def create_db():
    db.create_all()
    flash('Database created successfully!', 'info')
    return redirect(url_for('main.home'))


@current_app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', title="Oops! Page Not Found", error=error), 404


@current_app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html", title="Page Not Found")

