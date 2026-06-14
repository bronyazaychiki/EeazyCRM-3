from flask import render_template, flash, url_for, redirect, Blueprint, current_app
from eeazycrm import db
from flask_login import login_required, current_user
from sqlalchemy import func, cast, or_
from eeazycrm.deals.models import Deal, DealStage
from eeazycrm.accounts.models import Account
from eeazycrm.users.models import User
from datetime import datetime, date, timedelta

parser = None  # reserved for future config use

main = Blueprint('main', __name__)


@main.route("/")
@main.route("/home")
@login_required
def home():
    today = date.today()
    month_start = today.replace(day=1)

    # Base query helper: owner filter for non-admin
    def _filter(q):
        if not current_user.is_admin:
            q = q.filter(Deal.owner_id == current_user.id)
        return q

    # ---- KPI: total open pipeline ----
    closed_stage_filter = or_(
        DealStage.close_type.in_(['won', 'lost']),
        DealStage.stage_name.in_(['Closed - Won', 'Closed - Lost', 'Deal Won'])
    )
    open_q = _filter(
        Deal.query.join(Deal.deal_stage).filter(~closed_stage_filter)
    )
    pipeline_row = open_q.with_entities(
        func.coalesce(func.sum(Deal.expected_close_price), 0).label('total'),
        func.count(Deal.id).label('cnt')
    ).first()
    total_pipeline = float(pipeline_row.total)
    open_deal_count = pipeline_row.cnt

    # ---- KPI: deals won this month ----
    won_stage_filter = or_(
        DealStage.close_type == 'won',
        DealStage.stage_name.in_(['Closed - Won', 'Deal Won'])
    )
    won_q = _filter(
        Deal.query.join(Deal.deal_stage)
        .filter(won_stage_filter)
        .filter(Deal.expected_close_date.isnot(None))
        .filter(cast(Deal.expected_close_date, db.Date) >= month_start)
        .filter(cast(Deal.expected_close_date, db.Date) <= today)
    )
    won_row = won_q.with_entities(
        func.coalesce(func.sum(Deal.expected_close_price), 0).label('total'),
        func.count(Deal.id).label('cnt')
    ).first()
    won_this_month_total = float(won_row.total)
    won_this_month_count = won_row.cnt

    # ---- KPI: deals lost this month ----
    lost_stage_filter = or_(
        DealStage.close_type == 'lost',
        DealStage.stage_name == 'Closed - Lost'
    )
    lost_q = _filter(
        Deal.query.join(Deal.deal_stage)
        .filter(lost_stage_filter)
        .filter(Deal.expected_close_date.isnot(None))
        .filter(cast(Deal.expected_close_date, db.Date) >= month_start)
        .filter(cast(Deal.expected_close_date, db.Date) <= today)
    )
    lost_row = lost_q.with_entities(
        func.coalesce(func.sum(Deal.expected_close_price), 0).label('total'),
        func.count(Deal.id).label('cnt')
    ).first()
    lost_this_month_count = lost_row.cnt

    # ---- KPI: win rate (this month) ----
    total_closed = won_this_month_count + lost_this_month_count
    win_rate = (won_this_month_count / total_closed * 100) if total_closed > 0 else 0

    # ---- KPI: weighted forecast (open pipeline) ----
    stages_map = {s.id: s for s in DealStage.query.all()}
    open_deals = _filter(
        Deal.query.join(Deal.deal_stage).filter(~closed_stage_filter)
    ).with_entities(Deal.expected_close_price, Deal.deal_stage_id).all()

    weighted_total = 0.0
    for d in open_deals:
        stage = stages_map.get(d.deal_stage_id)
        order = (stage.display_order or 0) if stage else 0
        if order <= 1:
            prob = 0.10
        elif order == 2:
            prob = 0.25
        elif order == 3:
            prob = 0.50
        elif order == 4:
            prob = 0.75
        elif order >= 5:
            prob = 0.90
        else:
            prob = 0.10
        weighted_total += (d.expected_close_price or 0) * prob

    # ---- Deals closing in next 30 days ----
    upcoming_end = today + timedelta(days=30)
    upcoming = _filter(
        Deal.query.join(Deal.deal_stage)
        .filter(~closed_stage_filter)
        .filter(Deal.expected_close_date.isnot(None))
        .filter(cast(Deal.expected_close_date, db.Date) >= today)
        .filter(cast(Deal.expected_close_date, db.Date) <= upcoming_end)
    ).order_by(Deal.expected_close_date).limit(10).all()

    # ---- Stage distribution for mini chart ----
    stage_dist = _filter(
        Deal.query.join(Deal.deal_stage).filter(~closed_stage_filter)
    ).with_entities(
        DealStage.stage_name,
        func.count(Deal.id).label('cnt'),
        func.coalesce(func.sum(Deal.expected_close_price), 0).label('total')
    ).group_by(DealStage.stage_name).order_by(func.sum(Deal.expected_close_price).desc()).all()

    return render_template("index.html",
                           title="Dashboard",
                           total_pipeline=total_pipeline,
                           open_deal_count=open_deal_count,
                           won_this_month_total=won_this_month_total,
                           won_this_month_count=won_this_month_count,
                           lost_this_month_count=lost_this_month_count,
                           win_rate=win_rate,
                           weighted_total=weighted_total,
                           upcoming_deals=upcoming,
                           stage_distribution=stage_dist)


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
