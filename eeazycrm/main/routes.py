from flask import render_template, flash, url_for, redirect, Blueprint, current_app
from flask_login import current_user, login_required
from sqlalchemy import func, text
from datetime import datetime, timedelta

from eeazycrm import db
from eeazycrm.leads.models import Lead, LeadStatus
from eeazycrm.deals.models import Deal, DealStage
from eeazycrm.accounts.models import Account
from eeazycrm.contacts.models import Contact
from configparser import ConfigParser

parser = ConfigParser()

main = Blueprint('main', __name__)


def build_deal_stage_query(scope_to_user=True):
    """
    Aggregates deals by stage_name with SUM(expected_close_price) and COUNT(id).
    If scope_to_user=True AND current_user is not admin, filters to current_user's deals.
    Returns a SQLAlchemy query (call .all() on it).
    """
    base = Deal.query \
        .with_entities(
            DealStage.stage_name.label('stage_name'),
            func.sum(Deal.expected_close_price).label('total_price'),
            func.count(Deal.id).label('total_count')
        ) \
        .join(Deal.deal_stage)

    if scope_to_user and not current_user.is_admin:
        base = base \
            .group_by(DealStage.stage_name, Deal.owner_id) \
            .having(Deal.owner_id == current_user.id)
    else:
        base = base.group_by(DealStage.stage_name)

    return base.order_by(text('total_price DESC'))


@main.route("/")
@main.route("/home")
@login_required
def home():
    today = datetime.utcnow()
    thirty_days_ago = today - timedelta(days=30)
    seven_days_ahead = today + timedelta(days=7)

    # Owner scope filter for simple entity counts
    owner_filter = {} if current_user.is_admin else {'owner_id': current_user.id}

    # ---- KPI Cards ----
    total_leads = Lead.query.filter_by(**owner_filter).count()
    total_accounts = Account.query.filter_by(**owner_filter).count()
    total_contacts = Contact.query.filter_by(**owner_filter).count()

    # Open pipeline value (deals in open stages, i.e. close_type IS NULL)
    pipeline_query = Deal.query \
        .with_entities(
            func.sum(Deal.expected_close_price).label('total_value'),
            func.count(Deal.id).label('total_count')
        ) \
        .join(Deal.deal_stage) \
        .filter(DealStage.close_type == None)

    if not current_user.is_admin:
        pipeline_query = pipeline_query.filter(Deal.owner_id == current_user.id)

    pipeline = pipeline_query.first()
    pipeline_value = pipeline.total_value or 0.0
    pipeline_count = pipeline.total_count or 0

    # ---- New Leads (last 30 days, limit 5) ----
    new_leads = Lead.query \
        .filter_by(**owner_filter) \
        .filter(Lead.date_created >= thirty_days_ago) \
        .order_by(Lead.date_created.desc()) \
        .limit(5).all()

    # ---- Hot Leads needing follow-up (status Hot or Very Hot) ----
    hot_leads = Lead.query \
        .filter_by(**owner_filter) \
        .join(Lead.status) \
        .filter(LeadStatus.status_name.in_(['Hot', 'Very Hot'])) \
        .order_by(Lead.date_created.desc()) \
        .limit(5).all()

    # ---- Deals closing soon (next 7 days, open stages only) ----
    closing_deals_query = Deal.query \
        .join(Deal.deal_stage) \
        .filter(DealStage.close_type == None) \
        .filter(Deal.expected_close_date != None) \
        .filter(Deal.expected_close_date <= seven_days_ahead) \
        .filter(Deal.expected_close_date >= today)

    if not current_user.is_admin:
        closing_deals_query = closing_deals_query.filter(Deal.owner_id == current_user.id)

    closing_deals = closing_deals_query \
        .order_by(Deal.expected_close_date.asc()) \
        .limit(5).all()

    # ---- Recently Added Accounts (limit 5) ----
    recent_accounts = Account.query \
        .filter_by(**owner_filter) \
        .order_by(Account.date_created.desc()) \
        .limit(5).all()

    # ---- Chart Data: Deal Pipeline by Stage ----
    deal_stages_data = build_deal_stage_query(scope_to_user=True).all()

    return render_template(
        "index.html",
        title="Dashboard",
        today_date=today,
        total_leads=total_leads,
        total_accounts=total_accounts,
        total_contacts=total_contacts,
        pipeline_value=pipeline_value,
        pipeline_count=pipeline_count,
        new_leads=new_leads,
        hot_leads=hot_leads,
        closing_deals=closing_deals,
        recent_accounts=recent_accounts,
        deal_stages=deal_stages_data
    )


@main.route("/create_db")
def create_db():
    db.create_all()
    flash('Database created successfully!', 'info')
    return redirect(url_for('main.home'))


@current_app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html", title="Page Not Found")
