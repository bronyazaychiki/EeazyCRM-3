import pandas as pd
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from wtforms import Label

from flask import Blueprint, session, Response
from flask_login import current_user, login_required
from flask import render_template, flash, url_for, redirect, request

from eeazycrm import db
from .models import Lead
from eeazycrm.accounts.models import Account
from eeazycrm.contacts.models import Contact
from eeazycrm.deals.models import Deal
from eeazycrm.common.paginate import Paginate
from eeazycrm.common.filters import CommonFilters
from .filters import set_date_filters, set_source, set_status
from .forms import NewLead, ImportLeads, ConvertLead, \
    FilterLeads, BulkOwnerAssign, BulkLeadSourceAssign, BulkLeadStatusAssign, BulkDelete

from eeazycrm.rbac import check_access, is_admin

leads = Blueprint('leads', __name__)


def reset_lead_filters():
    if 'lead_owner' in session:
        session.pop('lead_owner', None)
    if 'lead_search' in session:
        session.pop('lead_search', None)
    if 'lead_date_created' in session:
        session.pop('lead_date_created', None)
    if 'lead_source' in session:
        session.pop('lead_source', None)
    if 'lead_status' in session:
        session.pop('lead_status', None)


@leads.route("/leads", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'view')
def get_leads_view():
    filters = FilterLeads()
    search = CommonFilters.set_search(filters, 'lead_search')
    owner = CommonFilters.set_owner(filters, 'Lead', 'lead_owner')
    advanced_filters = set_date_filters(filters, 'lead_date_created')
    source_filter = set_source(filters, 'lead_source')
    status_filter = set_status(filters, 'lead_status')

    query = Lead.query \
        .filter(or_(
            Lead.title.ilike(f'%{search}'),
            Lead.first_name.ilike(f'%{search}'),
            Lead.last_name.ilike(f'%{search}'),
            Lead.email.ilike(f'%{search}'),
            Lead.company_name.ilike(f'%{search}'),
            Lead.phone.ilike(f'%{search}'),
            Lead.mobile.ilike(f'%{search}'),
        ) if search else True) \
        .filter(source_filter) \
        .filter(status_filter) \
        .filter(owner) \
        .filter(advanced_filters) \
        .order_by(Lead.date_created.desc())

    bulk_form = {
        'owner': BulkOwnerAssign(),
        'lead_source': BulkLeadSourceAssign(),
        'lead_status': BulkLeadStatusAssign(),
        'delete': BulkDelete()
    }

    return render_template("leads/leads_list.html", title="Leads View",
                           leads=Paginate(query), filters=filters, bulk_form=bulk_form)


@leads.route("/leads/new", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'create')
def new_lead():
    form = NewLead()
    if request.method == 'POST':
        if form.validate_on_submit():
            lead = Lead(title=form.title.data,
                        first_name=form.first_name.data, last_name=form.last_name.data,
                        email=form.email.data, company_name=form.company.data,
                        address_line=form.address_line.data, addr_state=form.addr_state.data,
                        addr_city=form.addr_city.data, post_code=form.post_code.data,
                        country=form.country.data, source=form.lead_source.data,
                        status=form.lead_status.data, notes=form.notes.data)

            if current_user.is_admin:
                lead.owner = form.assignees.data
            else:
                lead.owner = current_user

            db.session.add(lead)
            db.session.commit()
            flash('New lead has been successfully created!', 'success')
            return redirect(url_for('leads.get_leads_view'))
        else:
            for error in form.errors:
                print(error)
            flash('Your form has errors! Please check the fields', 'danger')
    return render_template("leads/new_lead.html", title="New Lead", form=form)


@leads.route("/leads/edit/<int:lead_id>", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'update')
def update_lead(lead_id):
    lead = Lead.get_by_id(lead_id)
    if not lead:
        return redirect(url_for('leads.get_leads_view'))

    form = NewLead()
    if request.method == 'POST':
        if form.validate_on_submit():
            lead.title = form.title.data
            lead.first_name = form.first_name.data
            lead.last_name = form.last_name.data
            lead.email = form.email.data
            lead.company_name = form.company.data
            lead.phone = form.phone.data
            lead.mobile = form.mobile.data
            lead.address_line = form.address_line.data
            lead.addr_state = form.addr_state.data
            lead.addr_city = form.addr_city.data
            lead.post_code = form.post_code.data
            lead.country = form.country.data
            lead.owner = form.assignees.data
            lead.source = form.lead_source.data
            lead.status = form.lead_status.data
            lead.notes = form.notes.data
            db.session.commit()
            flash('The lead has been successfully updated', 'success')
            return redirect(url_for('leads.get_lead_view', lead_id=lead.id))
        else:
            print(form.errors)
            flash('User update failed! Form has errors', 'danger')
    elif request.method == 'GET':
        form.title.data = lead.title
        form.first_name.data = lead.first_name
        form.last_name.data = lead.last_name
        form.email.data = lead.email
        form.company.data = lead.company_name
        form.phone.data = lead.phone
        form.mobile.data = lead.mobile
        form.address_line.data = lead.address_line
        form.addr_state.data = lead.addr_state
        form.addr_city.data = lead.addr_city
        form.post_code.data = lead.post_code
        form.country.data = lead.country
        form.assignees.data = lead.owner
        form.lead_source.data = lead.source
        form.lead_status.data = lead.status
        form.notes.data = lead.notes
        form.submit.label = Label('update_lead', 'Update Lead')
    return render_template("leads/new_lead.html", title="Update Lead", form=form)


@leads.route("/leads/<int:lead_id>")
@login_required
@check_access('leads', 'view')
def get_lead_view(lead_id):
    lead = Lead.query.filter_by(id=lead_id).first()
    return render_template("leads/lead_view.html", title="View Lead", lead=lead)


@leads.route("/leads/del/<int:lead_id>")
@login_required
@check_access('leads', 'remove')
def delete_lead(lead_id):
    lead = Lead.query.filter_by(id=lead_id).first()
    if not lead:
        flash('The lead does not exist', 'danger')
    else:
        Lead.query.filter_by(id=lead_id).delete()
        db.session.commit()
        flash('The lead has been removed successfully', 'success')
    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/convert/<int:lead_id>", methods=['GET', 'POST'])
@login_required
@check_access('leads', 'view')
@check_access('accounts', 'create')
@check_access('contacts', 'create')
@check_access('deals', 'create')
def convert_lead(lead_id):
    lead = Lead.query.filter_by(id=lead_id).first()
    if not lead:
        flash('The lead does not exist', 'danger')
        return redirect(url_for('leads.get_leads_view'))

    if lead.is_converted:
        flash('This lead has already been converted and cannot be converted again.', 'warning')
        return redirect(url_for('leads.get_lead_view', lead_id=lead.id))

    form = ConvertLead()

    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                # --- Step A: Resolve Account ---
                if form.use_account_information.data:
                    # Creating a new account from lead information
                    # Check for duplicate by name
                    account = Account.query.filter_by(name=form.account_name.data.strip()).first()
                    if not account:
                        account = Account(
                            name=form.account_name.data.strip(),
                            email=form.account_email.data.strip(),
                            address_line=lead.address_line,
                            addr_state=lead.addr_state,
                            addr_city=lead.addr_city,
                            post_code=lead.post_code,
                            country=lead.country,
                            phone=lead.phone
                        )
                        if current_user.is_admin and form.assignees.data:
                            account.account_owner = form.assignees.data
                        else:
                            account.account_owner = current_user
                        db.session.add(account)
                else:
                    # Using an existing account from the dropdown
                    account = form.accounts.data

                # --- Step B: Resolve Contact ---
                contact = None
                if form.use_contact_information.data:
                    # Creating a new contact from lead information
                    # Check for duplicate by email (unique constraint)
                    existing_contact = Contact.query.filter_by(
                        email=form.contact_email.data.strip()
                    ).first()
                    if existing_contact:
                        # Reuse existing contact to avoid duplicate
                        contact = existing_contact
                    else:
                        contact = Contact(
                            first_name=form.contact_first_name.data.strip() if form.contact_first_name.data else lead.first_name,
                            last_name=form.contact_last_name.data.strip(),
                            email=form.contact_email.data.strip(),
                            phone=form.contact_phone.data.strip(),
                            mobile=lead.mobile,
                            address_line=lead.address_line,
                            addr_state=lead.addr_state,
                            addr_city=lead.addr_city,
                            post_code=lead.post_code,
                            country=lead.country
                        )
                        # Flush account first to get its ID
                        db.session.flush()
                        contact.account = account
                        if current_user.is_admin and form.assignees.data:
                            contact.contact_owner = form.assignees.data
                        else:
                            contact.contact_owner = current_user
                        db.session.add(contact)
                else:
                    # Using an existing contact from the dropdown
                    if form.contacts.data:
                        contact = form.contacts.data

                # Flush to ensure account and contact have IDs for deal FKs
                db.session.flush()

                # --- Step C: Create Deal (if requested) ---
                if form.create_deal.data:
                    deal = Deal(
                        title=form.title.data.strip(),
                        expected_close_price=form.expected_close_price.data,
                        expected_close_date=form.expected_close_date.data
                    )
                    deal.account = account
                    if contact:
                        deal.contact = contact
                    deal.dealstage = form.deal_stages.data
                    if current_user.is_admin and form.assignees.data:
                        deal.deal_owner = form.assignees.data
                    else:
                        deal.deal_owner = current_user
                    db.session.add(deal)

                # --- Step D: Mark lead as converted ---
                lead.is_converted = True
                lead.converted_date = datetime.utcnow()

                db.session.commit()
                flash('Lead has been successfully converted!', 'success')
                return redirect(url_for('leads.get_lead_view', lead_id=lead.id))

            except IntegrityError:
                db.session.rollback()
                flash('Conversion failed: a record with duplicate data already exists. '
                      'Please check the email and other fields for conflicts.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'Conversion failed due to an unexpected error. Please try again.', 'danger')
                print(f"Lead conversion error: {e}")
        else:
            flash('Your form has errors! Please check the fields', 'danger')
    else:
        # GET request — pre-populate form from lead data
        form.account_name.data = lead.company_name
        form.account_email.data = lead.email
        form.contact_first_name.data = lead.first_name
        form.contact_last_name.data = lead.last_name
        form.contact_email.data = lead.email
        form.contact_phone.data = lead.phone or lead.mobile
        form.title.data = lead.title

    return render_template("leads/lead_convert.html", title="Convert Lead", lead=lead, form=form)


@leads.route("/leads/import", methods=['GET', 'POST'])
@login_required
@is_admin
def import_bulk_leads():
    form = ImportLeads()
    if request.method == 'POST':
        ind = 0
        if form.validate_on_submit():
            data = pd.read_csv(form.csv_file.data)

            for _, row in data.iterrows():
                lead = Lead(first_name=row['first_name'], last_name=row['last_name'],
                            email=row['email'], company_name=row['company_name'])
                lead.owner = current_user
                if form.lead_source.data:
                    lead.source = form.lead_source.data
                db.session.add(lead)
                ind = ind + 1

            db.session.commit()
            flash(f'{ind} new lead(s) has been successfully imported!', 'success')
        else:
            flash('Your form has errors! Please check the fields', 'danger')
    return render_template("leads/leads_import.html", title="Import Leads", form=form)


@leads.route("/leads/reset_filters")
@login_required
@check_access('leads', 'view')
def reset_filters():
    reset_lead_filters()
    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/bulk_owner_assign", methods=['POST'])
@login_required
@is_admin
def bulk_owner_assign():
    form = BulkOwnerAssign()
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.owners_list.data:
                ids = [int(x) for x in request.form['leads_owner'].split(',')]
                Lead.query\
                    .filter(Lead.id.in_(ids))\
                    .update({
                        Lead.owner_id: form.owners_list.data.id
                    }, synchronize_session=False)
                db.session.commit()
                flash(f'Owner has been assigned to {len(ids)} lead(s) successfully!', 'success')
        else:
            print(form.errors)

    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/bulk_lead_source_assign", methods=['POST'])
@login_required
@is_admin
def bulk_lead_source_assign():
    form = BulkLeadSourceAssign()
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.lead_source_list.data:
                ids = [int(x) for x in request.form['leads_source'].split(',')]
                Lead.query \
                    .filter(Lead.id.in_(ids)) \
                    .update({
                        Lead.lead_source_id: form.lead_source_list.data.id
                    }, synchronize_session=False)
                db.session.commit()
                flash(f'Lead Source `{form.lead_source_list.data.source_name}` has been '
                      f'assigned to {len(ids)} lead(s) successfully!', 'success')
        else:
            print(form.errors)
    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/bulk_lead_status_assign", methods=['POST'])
@login_required
@is_admin
def bulk_lead_status_assign():
    form = BulkLeadStatusAssign()
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.lead_status_list.data:
                ids = [int(x) for x in request.form['leads_status'].split(',')]
                Lead.query \
                    .filter(Lead.id.in_(ids)) \
                    .update({
                        Lead.lead_status_id: form.lead_status_list.data.id
                    }, synchronize_session=False)
                db.session.commit()
                flash(f'Lead status `{form.lead_status_list.data.status_name}` has been '
                      f'assigned to {len(ids)} lead(s) successfully!', 'success')
        else:
            print(form.errors)
    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/bulk_delete", methods=['POST'])
@is_admin
def bulk_delete():
    form = BulkDelete()
    if request.method == 'POST':
        if form.validate_on_submit():
            ids = [int(x) for x in request.form['leads_to_delete'].split(',')]
            Lead.query \
                .filter(Lead.id.in_(ids)) \
                .delete(synchronize_session=False)
            db.session.commit()
            flash(f'Successfully deleted {len(ids)} lead(s)!', 'success')
        else:
            print(form.errors)
    return redirect(url_for('leads.get_leads_view'))


@leads.route("/leads/write_csv")
@login_required
def write_to_csv():
    ids = [int(x) for x in request.args.get('lead_ids').split(',')]
    query = Lead.query \
        .filter(Lead.id.in_(ids))
    csv = 'Title,Last Name,Email,Company Name,Phone,' \
          'Mobile,Owner,Lead Source,Lead Status,Date Created\n'
    for lead in query.all():
        csv += f'{lead.title},{lead.first_name},' \
               f'{lead.last_name},{lead.email},' \
               f'{lead.company_name},{lead.phone},{lead.mobile},' \
               f'{lead.owner.first_name} {lead.owner.last_name},' \
               f'{lead.source.source_name},{lead.status.status_name},' \
               f'{lead.date_created}\n'
    return Response(csv,
                    mimetype='text/csv',
                    headers={"Content-disposition":
                             "attachment; filename=leads.csv"})
