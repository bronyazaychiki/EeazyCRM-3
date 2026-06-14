from flask import Blueprint, session
from flask_login import current_user, login_required
from flask import render_template, flash, url_for, redirect, request
from sqlalchemy import or_
from wtforms import Label
from datetime import datetime

from eeazycrm import db
from .models import Activity, ActivityType, ActivityStatus
from eeazycrm.common.paginate import Paginate
from eeazycrm.common.filters import CommonFilters
from .forms import NewActivity, FilterActivities
from .filters import set_activity_type_filters, set_status_filters, set_date_filters

from eeazycrm.rbac import check_access
from eeazycrm.leads.models import Lead
from eeazycrm.accounts.models import Account
from eeazycrm.contacts.models import Contact
from eeazycrm.deals.models import Deal

activities = Blueprint('activities', __name__)


def reset_activities_filters():
    for key in ['activities_owner', 'activities_search', 'activities_type',
                'activities_status', 'activities_date']:
        if key in session:
            session.pop(key, None)


@activities.route("/activities", methods=['GET', 'POST'])
@login_required
@check_access('activities', 'view')
def get_activities_view():
    filters = FilterActivities()

    search = CommonFilters.set_search(filters, 'activities_search')
    owner = CommonFilters.set_owner(filters, 'Activity', 'activities_owner')
    type_filter = set_activity_type_filters(filters, 'activities_type')
    status_filter = set_status_filters(filters, 'activities_status')
    date_filter = set_date_filters(filters, 'Activity', 'activities_date')

    query = Activity.query.filter(or_(
        Activity.subject.ilike(f'%{search}%')
    ) if search else True) \
        .filter(type_filter) \
        .filter(status_filter) \
        .filter(date_filter) \
        .filter(owner) \
        .order_by(Activity.scheduled_date.asc())

    return render_template("activities/activities_list.html", title="Activities View",
                           activities=Paginate(query=query), filters=filters)


@activities.route("/activities/<int:activity_id>")
@login_required
@check_access('activities', 'view')
def get_activity_view(activity_id):
    activity = Activity.query.filter_by(id=activity_id).first()
    if not activity:
        return redirect(url_for('activities.get_activities_view'))
    return render_template("activities/activity_view.html", title="Activity View",
                           activity=activity)


@activities.route("/activities/new", methods=['GET', 'POST'])
@login_required
@check_access('activities', 'create')
def new_activity():
    form = NewActivity()

    # Context-aware pre-fill from query params
    if request.method == 'GET':
        lead_id = request.args.get('lead_id', None, type=int)
        account_id = request.args.get('account_id', None, type=int)
        contact_id = request.args.get('contact_id', None, type=int)
        deal_id = request.args.get('deal_id', None, type=int)

        if lead_id:
            lead = Lead.get_by_id(lead_id)
            if lead:
                form.leads.data = lead
        if account_id:
            account = Account.get_account(account_id)
            if account:
                form.accounts.data = account
        if contact_id:
            contact = Contact.get_contact(contact_id)
            if contact:
                form.contacts.data = contact
        if deal_id:
            deal = Deal.get_deal(deal_id)
            if deal:
                form.deals.data = deal

    if request.method == 'POST':
        if form.validate_on_submit():
            activity = Activity(
                subject=form.subject.data,
                scheduled_date=form.scheduled_date.data,
                status=form.status.data,
                priority=form.priority.data,
                description=form.description.data
            )

            activity.activity_type = form.activity_type.data

            if form.leads.data:
                activity.lead = form.leads.data
            if form.accounts.data:
                activity.account = form.accounts.data
            if form.contacts.data:
                activity.contact = form.contacts.data
            if form.deals.data:
                activity.deal = form.deals.data

            if current_user.is_admin:
                activity.owner = form.assignees.data
            else:
                activity.owner = current_user

            if activity.status == ActivityStatus.COMPLETED:
                activity.completed_date = datetime.utcnow()

            db.session.add(activity)
            db.session.commit()
            flash('Activity has been successfully created!', 'success')
            return redirect(url_for('activities.get_activities_view'))
        else:
            for error in form.errors:
                print(error)
            flash('Your form has errors! Please check the fields', 'danger')

    return render_template("activities/new_activity.html", title="New Activity", form=form)


@activities.route("/activities/edit/<int:activity_id>", methods=['GET', 'POST'])
@login_required
@check_access('activities', 'update')
def update_activity(activity_id):
    activity = Activity.get_by_id(activity_id)
    if not activity:
        return redirect(url_for('activities.get_activities_view'))

    form = NewActivity()
    if request.method == 'POST':
        if form.validate_on_submit():
            activity.subject = form.subject.data
            activity.scheduled_date = form.scheduled_date.data
            activity.status = form.status.data
            activity.priority = form.priority.data
            activity.description = form.description.data
            activity.activity_type = form.activity_type.data

            activity.lead = form.leads.data
            activity.account = form.accounts.data
            activity.contact = form.contacts.data
            activity.deal = form.deals.data

            if current_user.is_admin:
                activity.owner = form.assignees.data

            # Handle completed_date
            if activity.status == ActivityStatus.COMPLETED:
                if not activity.completed_date:
                    activity.completed_date = datetime.utcnow()
            else:
                activity.completed_date = None

            db.session.commit()
            flash('Activity has been successfully updated!', 'success')
            return redirect(url_for('activities.get_activity_view', activity_id=activity.id))
        else:
            print(form.errors)
            flash('Activity update failed! Form has errors', 'danger')
    elif request.method == 'GET':
        form.subject.data = activity.subject
        form.activity_type.data = activity.activity_type
        form.scheduled_date.data = activity.scheduled_date
        form.status.data = activity.status
        form.priority.data = activity.priority
        form.description.data = activity.description
        form.leads.data = activity.lead
        form.accounts.data = activity.account
        form.contacts.data = activity.contact
        form.deals.data = activity.deal
        form.assignees.data = activity.owner
        form.submit.label = Label('update_activity', 'Update Activity')

    return render_template("activities/new_activity.html", title="Update Activity", form=form)


@activities.route("/activities/del/<int:activity_id>")
@login_required
@check_access('activities', 'remove')
def delete_activity(activity_id):
    Activity.query.filter_by(id=activity_id).delete()
    db.session.commit()
    flash('Activity removed successfully!', 'success')
    return redirect(url_for('activities.get_activities_view'))


@activities.route("/activities/complete/<int:activity_id>")
@login_required
@check_access('activities', 'update')
def complete_activity(activity_id):
    activity = Activity.query.filter_by(id=activity_id).first()
    if activity:
        activity.status = ActivityStatus.COMPLETED
        activity.completed_date = datetime.utcnow()
        db.session.commit()
        flash('Activity marked as completed!', 'success')
    return redirect(url_for('activities.get_activities_view'))


@activities.route("/activities/reset_filters")
@login_required
@check_access('activities', 'view')
def reset_filters():
    reset_activities_filters()
    return redirect(url_for('activities.get_activities_view'))
