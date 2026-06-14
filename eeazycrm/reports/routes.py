from flask import Blueprint, render_template, request, Response
from flask_login import current_user, login_required
from sqlalchemy import func, text, cast, Date
from eeazycrm import db
from eeazycrm.deals.models import Deal, DealStage
from eeazycrm.accounts.models import Account
from eeazycrm.users.models import User
from eeazycrm.rbac import is_admin
from datetime import datetime, timedelta, date
from collections import OrderedDict
import csv
import io
from functools import reduce

reports = Blueprint('reports', __name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _period_start(period):
    """Return (start_date, end_date) for a given period shorthand."""
    today = date.today()
    end = today
    mapping = {
        '7d': timedelta(days=7),
        '30d': timedelta(days=30),
        '90d': timedelta(days=90),
        '1y': timedelta(days=365),
    }
    delta = mapping.get(period, timedelta(days=30))
    return today - delta, end


def _truncate_date(dt, granularity):
    """Truncate a datetime to the requested granularity string key."""
    if dt is None:
        return None
    if granularity == 'day':
        return dt.strftime('%Y-%m-%d')
    elif granularity == 'week':
        iso = dt.isocalendar()
        return f'{iso[0]}-W{iso[1]:02d}'
    else:  # month
        return dt.strftime('%Y-%m')


def _stage_probability(stage):
    """Return a 0-1 probability weight for an open deal stage."""
    if stage is None:
        return 0.10
    name = stage.stage_name.lower()
    ct = (stage.close_type or '').lower()

    if ct == 'won' or 'won' in name:
        return 1.0
    if ct == 'lost' or 'lost' in name:
        return 0.0

    order = stage.display_order or 0
    if order <= 1:
        return 0.10
    elif order == 2:
        return 0.25
    elif order == 3:
        return 0.50
    elif order == 4:
        return 0.75
    elif order >= 5:
        return 0.90
    return 0.10


def _apply_owner_filter(query, model_cls):
    """If the current user is not admin, restrict to their own deals."""
    if not current_user.is_admin:
        query = query.filter(model_cls.owner_id == current_user.id)
    return query


# ---------------------------------------------------------------------------
# Reports index
# ---------------------------------------------------------------------------

@reports.route("/reports/deals")
@login_required
def deal_reports():
    return render_template("reports/reports.html", title="Reports")


# ---------------------------------------------------------------------------
# Net revenue by deal stages  (existing — untouched)
# ---------------------------------------------------------------------------

@reports.route("/reports/deal_stages")
@login_required
def deal_stages():
    if current_user.is_admin:
        query = Deal.query \
            .with_entities(
                DealStage.stage_name.label('stage_name'),
                func.sum(Deal.expected_close_price).label('total_price'),
                func.count(Deal.id).label('total_count')
            ) \
            .join(Deal.deal_stage) \
            .group_by(DealStage.stage_name) \
            .order_by(text('total_price DESC'))
    else:
        query = Deal.query \
            .with_entities(
                DealStage.stage_name.label('stage_name'),
                func.sum(Deal.expected_close_price).label('total_price'),
                func.count(Deal.id).label('total_count')
            ) \
            .join(Deal.deal_stage) \
            .group_by(DealStage.stage_name, Deal.owner_id) \
            .having(Deal.owner_id == current_user.id) \
            .order_by(text('total_price DESC'))

    return render_template("reports/deals_stages.html",
                           title="Reports: Deal Stages", deals=query.all())


# ---------------------------------------------------------------------------
# Deal stage revenue by account  (existing — untouched)
# ---------------------------------------------------------------------------

@reports.route("/reports/deals_closed")
@login_required
def deals_closed():
    if current_user.is_admin:
        query = Deal.query \
            .with_entities(
                Account.name.label('account_name'),
                DealStage.stage_name.label('stage_name'),
                func.sum(Deal.expected_close_price).label('total_price'),
                func.count(Deal.id).label('total_count')
            ) \
            .join(Deal.account, Deal.deal_stage) \
            .group_by(Account.name, DealStage.stage_name) \
            .order_by(text('stage_name'))
    else:
        query = Deal.query \
            .with_entities(
                Account.name.label('account_name'),
                DealStage.stage_name.label('stage_name'),
                func.sum(Deal.expected_close_price).label('total_price'),
                func.count(Deal.id).label('total_count')
            ) \
            .join(Deal.account, Deal.deal_stage) \
            .group_by(Account.name, DealStage.stage_name, Deal.owner_id) \
            .having(Deal.owner_id == current_user.id) \
            .order_by(text('stage_name'))

    stages = []
    data = []
    rows = query.all()
    if len(rows) > 0:
        for d in rows:
            if d[1] not in stages:
                stages.append(d[1])
                data.append({
                    'stage_name': d[1],
                    'accounts_count': len([x[1] for x in rows if x[1] == d[1]]),
                    'rows': [(x[0], x[2], x[3]) for x in rows if x[1] == d[1]]
                })

    return render_template("reports/deals_closed.html",
                           title="Reports: Deals Stages by Accounts", deals=data)


# ---------------------------------------------------------------------------
# Deal stages by users  (existing — untouched, admin only)
# ---------------------------------------------------------------------------

def get_users_deals():
    users_list = Deal.query \
        .with_entities(
            Deal.owner_id.label('owner'),
            User.first_name,
            User.last_name,
            DealStage.stage_name,
            func.sum(Deal.expected_close_price).label('total_price')
        ) \
        .filter(DealStage.stage_name.in_(['Closed - Won', 'Closed - Lost'])) \
        .join(Deal.owner, Deal.deal_stage) \
        .group_by(Deal.owner_id, User.first_name, User.last_name, DealStage.stage_name) \
        .order_by(text('owner'))

    won_list = [x for x in users_list.all() if x.stage_name == 'Closed - Won']
    lost_list = [x for x in users_list.all() if x.stage_name == 'Closed - Lost']
    return won_list, lost_list


@reports.route("/reports/deal_stage_by_users")
@login_required
@is_admin
def deal_stage_by_users():
    query = Deal.query \
        .with_entities(
            Deal.owner_id.label('owner'),
            User.first_name,
            User.last_name,
            DealStage.stage_name.label('stage_name'),
            func.sum(Deal.expected_close_price).label('total_price'),
            func.count(Deal.id).label('total_count')
        ) \
        .join(Deal.owner, Deal.deal_stage) \
        .group_by(Deal.owner_id, User.first_name, User.last_name, DealStage.stage_name) \
        .order_by(text('owner'))

    users = []
    data = []
    rows = query.all()
    if len(rows) > 0:
        for d in rows:
            if d[0] not in users:
                users.append(d[0])
                data.append({
                    'owner': f'{d[1]} {d[2]}',
                    'count': len([x[3] for x in rows if x[0] == d[0]]),
                    'rows': [(x[3], x[4], x[5]) for x in rows if x[0] == d[0]],
                    'total_cost': reduce(lambda a, b: a + b, [x[4] for x in rows if x[0] == d[0]]),
                    'total_qty': reduce(lambda a, b: a + b, [x[5] for x in rows if x[0] == d[0]])
                })

    return render_template("reports/deals_stage_by_users.html",
                           title="Reports: Deal Stages by Users",
                           deals=data,
                           deals_closed=get_users_deals())


# ---------------------------------------------------------------------------
# Deals closed by time  (NEW — replaces broken deal_closed_by_date)
# ---------------------------------------------------------------------------

@reports.route("/reports/deal_closed_by_date")
@login_required
def deal_closed_by_date():
    period = request.args.get('period', '30d')
    granularity = request.args.get('granularity', 'day')
    export = request.args.get('export', '')

    date_from, date_to = _period_start(period)

    # Base query — all won / lost deals in the date window
    query = Deal.query.with_entities(
        Deal.id,
        Deal.title,
        Deal.expected_close_price,
        Deal.expected_close_date,
        DealStage.stage_name,
        DealStage.close_type,
        User.first_name,
        User.last_name,
        Account.name.label('account_name'),
    ).join(Deal.deal_stage) \
     .outerjoin(Deal.owner) \
     .outerjoin(Deal.account)

    # Only closed deals (use close_type for robustness)
    query = query.filter(
        db.or_(
            DealStage.close_type.in_(['won', 'lost']),
            DealStage.stage_name.in_(['Closed - Won', 'Closed - Lost', 'Deal Won'])
        )
    )

    # Date range filter
    query = query.filter(Deal.expected_close_date.isnot(None))
    query = query.filter(
        cast(Deal.expected_close_date, Date) >= date_from
    )
    query = query.filter(
        cast(Deal.expected_close_date, Date) <= date_to
    )

    # Owner filter for non-admin
    if not current_user.is_admin:
        query = query.filter(Deal.owner_id == current_user.id)

    rows = query.order_by(Deal.expected_close_date).all()

    # --- CSV export ---
    if export == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Date', 'Deal Title', 'Account', 'Owner',
                         'Stage', 'Amount'])
        for r in rows:
            close_date = r.expected_close_date.strftime('%Y-%m-%d') if r.expected_close_date else ''
            owner = f'{r.first_name or ""} {r.last_name or ""}'.strip()
            writer.writerow([close_date, r.title or '', r.account_name or '',
                             owner, r.stage_name,
                             f'{r.expected_close_price:.2f}'])
        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = \
            f'attachment; filename=deals_closed_{period}.csv'
        return response

    # --- Group by time bucket ---
    won_buckets = OrderedDict()
    lost_buckets = OrderedDict()
    won_total = 0.0
    lost_total = 0.0
    won_count = 0
    lost_count = 0

    for r in rows:
        key = _truncate_date(r.expected_close_date, granularity)
        if key is None:
            continue

        is_won = (r.close_type == 'won') or \
                 r.stage_name in ('Closed - Won', 'Deal Won')

        if is_won:
            bucket = won_buckets
            won_total += (r.expected_close_price or 0)
            won_count += 1
        else:
            bucket = lost_buckets
            lost_total += (r.expected_close_price or 0)
            lost_count += 1

        if key not in bucket:
            bucket[key] = {'count': 0, 'total': 0.0}
        bucket[key]['count'] += 1
        bucket[key]['total'] += (r.expected_close_price or 0)

    # Build ordered chart arrays
    all_keys = sorted(set(list(won_buckets.keys()) + list(lost_buckets.keys())))
    labels = all_keys
    won_values = [round(won_buckets.get(k, {}).get('total', 0), 2) for k in all_keys]
    lost_values = [round(lost_buckets.get(k, {}).get('total', 0), 2) for k in all_keys]
    won_counts = [won_buckets.get(k, {}).get('count', 0) for k in all_keys]
    lost_counts = [lost_buckets.get(k, {}).get('count', 0) for k in all_keys]

    return render_template("reports/deals_closed_by_time.html",
                           title="Reports: Deals Closed by Time",
                           rows=rows,
                           labels=labels,
                           won_values=won_values,
                           lost_values=lost_values,
                           won_counts=won_counts,
                           lost_counts=lost_counts,
                           won_total=won_total,
                           lost_total=lost_total,
                           won_count=won_count,
                           lost_count=lost_count,
                           current_period=period,
                           current_granularity=granularity,
                           date_from=date_from,
                           date_to=date_to)


# ---------------------------------------------------------------------------
# Sales forecast  (NEW)
# ---------------------------------------------------------------------------

@reports.route("/reports/sales_forecast")
@login_required
def sales_forecast():
    granularity = request.args.get('granularity', 'month')
    export = request.args.get('export', '')

    # Fetch all deals (open + closed) to compute pipeline
    query = Deal.query.with_entities(
        Deal.id,
        Deal.title,
        Deal.expected_close_price,
        Deal.expected_close_date,
        DealStage.stage_name,
        DealStage.close_type,
        DealStage.display_order,
        User.first_name,
        User.last_name,
        Account.name.label('account_name'),
    ).join(Deal.deal_stage) \
     .outerjoin(Deal.owner) \
     .outerjoin(Deal.account)

    if not current_user.is_admin:
        query = query.filter(Deal.owner_id == current_user.id)

    rows = query.order_by(Deal.expected_close_date).all()

    # Build stage objects for probability lookup
    stages_cache = {}
    for s in DealStage.query.all():
        stages_cache[s.id] = s

    # Classify and compute
    open_deals = []
    total_pipeline = 0.0
    total_weighted = 0.0

    # Group open deals by time bucket
    forecast_buckets = OrderedDict()

    for r in rows:
        ct = (r.close_type or '').lower()
        stage_name = r.stage_name or ''
        is_closed = ct in ('won', 'lost') or \
                    stage_name in ('Closed - Won', 'Closed - Lost', 'Deal Won')

        if is_closed:
            continue  # skip closed deals for forecast

        price = r.expected_close_price or 0
        total_pipeline += price

        # Compute probability from display_order (passed in query)
        order = r.display_order or 0
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

        weighted = price * prob
        total_weighted += weighted

        open_deals.append({
            'title': r.title,
            'account': r.account_name,
            'owner': f'{r.first_name or ""} {r.last_name or ""}'.strip(),
            'stage': stage_name,
            'price': price,
            'probability': prob,
            'weighted': weighted,
            'close_date': r.expected_close_date,
        })

        # Group into bucket by expected close date
        key = _truncate_date(r.expected_close_date, granularity) if r.expected_close_date else 'No Date'
        if key not in forecast_buckets:
            forecast_buckets[key] = {
                'pipeline': 0.0,
                'weighted': 0.0,
                'count': 0,
            }
        forecast_buckets[key]['pipeline'] += price
        forecast_buckets[key]['weighted'] += weighted
        forecast_buckets[key]['count'] += 1

    # Sort buckets
    sorted_keys = sorted(forecast_buckets.keys(),
                         key=lambda k: k if k != 'No Date' else '9999')
    labels = sorted_keys
    pipeline_values = [round(forecast_buckets[k]['pipeline'], 2) for k in sorted_keys]
    weighted_values = [round(forecast_buckets[k]['weighted'], 2) for k in sorted_keys]
    deal_counts = [forecast_buckets[k]['count'] for k in sorted_keys]

    # Stage breakdown summary
    stage_summary = {}
    for d in open_deals:
        s = d['stage'] or 'Unassigned'
        if s not in stage_summary:
            stage_summary[s] = {'count': 0, 'pipeline': 0.0, 'weighted': 0.0,
                                'probability': d['probability']}
        stage_summary[s]['count'] += 1
        stage_summary[s]['pipeline'] += d['price']
        stage_summary[s]['weighted'] += d['weighted']

    # --- CSV export ---
    if export == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Expected Close Date', 'Deal Title', 'Account',
                         'Owner', 'Stage', 'Probability %',
                         'Amount', 'Weighted Amount'])
        for d in open_deals:
            close_date = d['close_date'].strftime('%Y-%m-%d') if d['close_date'] else ''
            writer.writerow([close_date, d['title'] or '', d['account'] or '',
                             d['owner'], d['stage'],
                             f"{d['probability']*100:.0f}",
                             f"{d['price']:.2f}",
                             f"{d['weighted']:.2f}"])
        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = \
            'attachment; filename=sales_forecast.csv'
        return response

    return render_template("reports/sales_forecast.html",
                           title="Reports: Sales Forecast",
                           open_deals=open_deals,
                           labels=labels,
                           pipeline_values=pipeline_values,
                           weighted_values=weighted_values,
                           deal_counts=deal_counts,
                           total_pipeline=total_pipeline,
                           total_weighted=total_weighted,
                           stage_summary=stage_summary,
                           current_granularity=granularity)
