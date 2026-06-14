from flask import Blueprint
from flask_login import current_user, login_required
from flask import render_template, flash, url_for, redirect, request
from sqlalchemy.exc import IntegrityError

from eeazycrm.users.forms import UpdateProfile, UpdateRoleForm, NewRoleForm, UpdateUser, ResourceForm
from eeazycrm.users.utils import upload_avatar
from eeazycrm.users.models import User, Role, Resource

from eeazycrm.leads.models import LeadSource, LeadStatus
from eeazycrm.deals.models import DealStage
from eeazycrm.settings.config_forms import LeadSourceForm, LeadStatusForm, DealStageForm

from eeazycrm import db, bcrypt
from eeazycrm.rbac import check_access, is_admin

settings = Blueprint('settings', __name__)


@settings.route("/settings/profile", methods=['GET', 'POST'])
@login_required
def settings_profile():
    form = UpdateProfile()
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.picture.data:
                picture_file = upload_avatar(current_user, form.picture.data)
                current_user.avatar = picture_file
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.email = form.email.data
            db.session.commit()
            flash('Your account information has been successfully updated', 'success')
            return redirect(url_for('settings.settings_profile'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    return render_template("settings/profile.html", title="My Profile", form=form)


# get all users except the current one (admin)
@settings.route("/settings/staff")
@login_required
@check_access("staff", "view")
def settings_staff_list():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    users = User.query\
        .filter(User.id != current_user.id)\
        .order_by(User.id.asc())\
        .paginate(per_page=per_page, page=page)
    return render_template("settings/staff_list.html", title="User Management", users=users)


@settings.route("/settings/staff/<int:user_id>")
@login_required
@check_access("staff", "view")
def settings_staff_view(user_id):
    user = User.query.filter(User.id == user_id).first()
    return render_template("settings/staff_view.html", title="View Staff", user=user)


@settings.route("/settings/staff/edit/<int:user_id>", methods=['GET', 'POST'])
@login_required
@check_access("staff", "update")
def settings_staff_update(user_id):
    form = UpdateUser()
    user = User.query.filter(User.id == user_id).first()

    acl = Role.query\
        .with_entities(Role.id,
                       Resource.id,
                       Resource.name,
                       Resource.can_view,
                       Resource.can_create,
                       Resource.can_edit,
                       Resource.can_delete)\
        .filter_by(id=user.role_id)\
        .join(Role.resources)\
        .order_by(Resource.id.asc())\
        .all()

    if request.method == 'POST':
        if form.validate_on_submit():
            if form.picture.data:
                picture_file = upload_avatar(user, form.picture.data)
                user.avatar = picture_file
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.email = form.email.data
            user.role = form.role.data
            user.is_user_active = form.is_user_active.data
            user.is_first_login = form.is_first_login.data

            for permission in form.permissions:
                resource = Resource.query.filter_by(id=permission.resource_id.data).first()
                resource.can_view = permission.can_view.data
                resource.can_create = permission.can_create.data
                resource.can_edit = permission.can_edit.data
                resource.can_delete = permission.can_delete.data

            try:
                db.session.commit()
                flash('Staff member information has been successfully updated', 'success')
                return redirect(url_for('settings.settings_staff_view', user_id=user.id))
            except IntegrityError:
                db.session.rollback()
                form.email.errors = [f'Email \'{form.email.data}\' already exists!']
                flash('User update failed! Form has errors', 'danger')

        else:
            print(form.errors)
            flash('User update failed! Form has errors', 'danger')
    elif request.method == 'GET':
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.email.data = user.email
        if user.avatar:
            form.picture.data = user.avatar
        form.role.data = user.role
        form.is_user_active.data = user.is_user_active
        form.is_first_login.data = user.is_first_login

        for l in acl:
            resource_form = ResourceForm()
            resource_form.resource_id = l.id
            resource_form.name = l.name
            resource_form.can_view = l.can_view
            resource_form.can_create = l.can_create
            resource_form.can_edit = l.can_edit
            resource_form.can_delete = l.can_delete
            form.permissions.append_entry(resource_form)

    return render_template("settings/staff_update.html", title="Update Staff", form=form)


@settings.route("/settings/staff/new", methods=['GET', 'POST'])
@login_required
@check_access("staff", "create")
def settings_staff_new():
    form = UpdateUser()
    if request.method == 'POST':
        hashed_pwd = bcrypt.generate_password_hash('123').decode('utf-8')
        if form.validate_on_submit():
            user = User()
            user.first_name = form.first_name.data
            user.last_name = form.last_name.data
            user.email = form.email.data
            user.password = hashed_pwd
            if form.picture.data:
                picture_file = upload_avatar(user, form.picture.data)
                user.avatar = picture_file
            user.role = form.role.data
            user.is_user_active = form.is_user_active.data
            user.is_first_login = form.is_first_login.data

            db.session.add(user)
            db.session.commit()
            flash('User has been successfully created!', 'success')
            return redirect(url_for('settings.settings_staff_list'))
        else:
            print(form.errors)
            flash(f'Failed to register user!', 'danger')
    return render_template("settings/new_user.html", title="New Staff Member", form=form)


@settings.route("/settings/staff/del/<int:user_id>")
@login_required
@check_access("staff", "remove")
def settings_staff_remove(user_id):
    User.query.filter(User.id == user_id).delete()
    db.session.commit()
    return redirect(url_for('main.home'))


@settings.route("/settings/staff/del/<email>", methods=['DELETE'])
@login_required
@check_access("staff", "remove")
def settings_staff_remove_by_email(email):
    User.query.filter(User.email == email).delete()
    db.session.commit()
    flash('User removed successfully!', 'success')
    return redirect(url_for('main.home'))


@settings.route("/settings/email", methods=['GET', 'POST'])
@login_required
def email_settings():
    flash('Email settings saved', 'success')
    return redirect(url_for('main.home'))


@settings.route("/settings/roles")
@login_required
@is_admin
def settings_roles_view():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    roles = Role.query\
        .filter(Role.name != 'admin')\
        .order_by(Role.id.asc())\
        .paginate(per_page=per_page, page=page)
    return render_template("settings/roles_list.html", title="Roles & Permissions", roles=roles)


@settings.route("/settings/role/new", methods=['GET', 'POST'])
@login_required
@is_admin
def settings_roles_new():
    form = NewRoleForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            role = Role()
            role.name = form.name.data

            for permission in form.permissions:
                resource = Resource()
                resource.name = permission.form.name.data
                resource.can_view = permission.form.can_view.data
                resource.can_create = permission.form.can_create.data
                resource.can_edit = permission.form.can_edit.data
                resource.can_delete = permission.form.can_delete.data
                role.resources.append(resource)

            db.session.add(role)
            db.session.commit()

            flash('Role has been successfully created!', 'success')
            return redirect(url_for('settings.settings_roles_view'))
        else:
            flash('Failed to create new role!', 'danger')
    elif request.method == 'GET':
        resources = [
            ResourceForm(name='staff', can_view=False,
                         can_create=False, can_edit=False, can_delete=False),
            ResourceForm(name='leads', can_view=True,
                         can_create=True, can_edit=True, can_delete=True)
        ]

        for resource in resources:
            form.permissions.append_entry(resource.data)
    return render_template("settings/role_new.html", title="Create New Role", form=form)


@settings.route("/settings/role/edit/<role_id>", methods=['GET', 'POST'])
@login_required
@is_admin
def settings_roles_update(role_id):
    role = Role.query.filter_by(id=role_id).first()
    form = UpdateRoleForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            role.name = form.name.data.lower()
            role.set_permissions(form.permissions)

            try:
                db.session.commit()
                flash('Role successfully created!', 'success')
                return redirect(url_for('settings.settings_roles_view'))
            except IntegrityError:
                db.session.rollback()
                if form.name.data == 'admin':
                    form.name.errors = [f'The role \'{form.name.data}\' is reserved by the system ! Please choose a different name']
                else:
                    form.name.errors = [f'The role \'{form.name.data}\' already exists ! Please choose a different name']
                flash('Failed to create new role!', 'danger')

        else:
            flash('Failed to create new role!', 'danger')
    elif request.method == 'GET':
        form.name.data = role.name
        for resource in role.resources:
            resource_form = ResourceForm()
            resource_form.name = resource.name
            resource_form.can_view = resource.can_view
            resource_form.can_create = resource.can_create
            resource_form.can_edit = resource.can_edit
            resource_form.can_delete = resource.can_delete
            form.permissions.append_entry(resource_form)

    return render_template("settings/role_update.html", title="Update Role", form=form)


@settings.route("/settings/roles/del/<role_id>")
@login_required
@is_admin
def settings_roles_remove(role_id):
    role = Role.query.filter_by(id=role_id).first()
    db.session.delete(role)
    db.session.commit()
    return redirect(url_for('settings.settings_roles_view'))


# just for testing
@settings.route("/settings/resource/create")
@login_required
@is_admin
def create_resource():
    roles = Role.query \
        .filter(Role.name != 'admin') \
        .order_by(Role.id.asc())

    resources = ['staff', 'leads', 'accounts', 'contacts', 'deals']

    for role in roles:
        for res in resources:
            resource = Resource()
            resource.name = res
            resource.can_view = False
            resource.can_create = False
            resource.can_edit = False
            resource.can_delete = False
            role.resources.append(resource)

    db.session.add(role)
    db.session.commit()


# ─────────────────────────────────────────────────────────
#  Configuration Management
# ─────────────────────────────────────────────────────────

def _reorder_config_item(model_class, item_id, direction):
    """Swap display_order of item with its neighbor."""
    item = model_class.query.get(item_id)
    if not item:
        return

    if direction == 'up':
        neighbor = model_class.query \
            .filter(model_class.display_order < item.display_order) \
            .order_by(model_class.display_order.desc()) \
            .first()
    else:
        neighbor = model_class.query \
            .filter(model_class.display_order > item.display_order) \
            .order_by(model_class.display_order.asc()) \
            .first()

    if neighbor:
        item.display_order, neighbor.display_order = neighbor.display_order, item.display_order
        db.session.commit()


# ── Config Hub ──

@settings.route("/settings/config")
@login_required
@is_admin
def config():
    sources_total = LeadSource.query.count()
    sources_active = LeadSource.query.filter_by(is_active=True).count()
    statuses_total = LeadStatus.query.count()
    statuses_active = LeadStatus.query.filter_by(is_active=True).count()
    stages_total = DealStage.query.count()
    stages_active = DealStage.query.filter_by(is_active=True).count()
    return render_template("settings/config_hub.html",
                           title="Configuration Management",
                           sources_active=sources_active, sources_total=sources_total,
                           statuses_active=statuses_active, statuses_total=statuses_total,
                           stages_active=stages_active, stages_total=stages_total)


# ── Lead Sources ──

@settings.route("/settings/config/lead_sources")
@login_required
@is_admin
def config_lead_sources():
    sources = LeadSource.lead_source_query_all().all()
    return render_template("settings/config_lead_sources.html",
                           title="Lead Sources", sources=sources)


@settings.route("/settings/config/lead_source/new", methods=['GET', 'POST'])
@login_required
@is_admin
def config_lead_source_new():
    form = LeadSourceForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            max_order = db.session.query(db.func.max(LeadSource.display_order)).scalar() or 0
            source = LeadSource(
                source_name=form.source_name.data,
                is_active=form.is_active.data,
                display_order=max_order + 1
            )
            db.session.add(source)
            try:
                db.session.commit()
                flash('Lead source has been successfully created!', 'success')
                return redirect(url_for('settings.config_lead_sources'))
            except IntegrityError:
                db.session.rollback()
                form.source_name.errors = ['A lead source with this name already exists.']
                flash('Failed to create lead source.', 'danger')
    return render_template("settings/config_lead_source_form.html",
                           title="New Lead Source", form=form)


@settings.route("/settings/config/lead_source/edit/<int:source_id>", methods=['GET', 'POST'])
@login_required
@is_admin
def config_lead_source_edit(source_id):
    source = LeadSource.get_by_id(source_id)
    if not source:
        flash('Lead source not found.', 'danger')
        return redirect(url_for('settings.config_lead_sources'))

    form = LeadSourceForm(exclude_id=source_id)
    if request.method == 'POST':
        if form.validate_on_submit():
            source.source_name = form.source_name.data
            source.is_active = form.is_active.data
            try:
                db.session.commit()
                flash('Lead source has been successfully updated!', 'success')
                return redirect(url_for('settings.config_lead_sources'))
            except IntegrityError:
                db.session.rollback()
                form.source_name.errors = ['A lead source with this name already exists.']
                flash('Failed to update lead source.', 'danger')
    else:
        form.source_name.data = source.source_name
        form.is_active.data = source.is_active
    return render_template("settings/config_lead_source_form.html",
                           title="Edit Lead Source", form=form, source=source)


@settings.route("/settings/config/lead_source/del/<int:source_id>")
@login_required
@is_admin
def config_lead_source_delete(source_id):
    source = LeadSource.get_by_id(source_id)
    if not source:
        flash('Lead source not found.', 'danger')
    elif source.leads:
        flash(f'Cannot delete \'{source.source_name}\': {len(source.leads)} lead(s) reference it. '
              'Please disable it instead.', 'warning')
    else:
        db.session.delete(source)
        db.session.commit()
        flash('Lead source has been removed.', 'success')
    return redirect(url_for('settings.config_lead_sources'))


@settings.route("/settings/config/lead_source/move_up/<int:source_id>")
@login_required
@is_admin
def config_lead_source_move_up(source_id):
    _reorder_config_item(LeadSource, source_id, direction='up')
    return redirect(url_for('settings.config_lead_sources'))


@settings.route("/settings/config/lead_source/move_down/<int:source_id>")
@login_required
@is_admin
def config_lead_source_move_down(source_id):
    _reorder_config_item(LeadSource, source_id, direction='down')
    return redirect(url_for('settings.config_lead_sources'))


# ── Lead Statuses ──

@settings.route("/settings/config/lead_statuses")
@login_required
@is_admin
def config_lead_statuses():
    statuses = LeadStatus.lead_status_query_all().all()
    return render_template("settings/config_lead_statuses.html",
                           title="Lead Statuses", statuses=statuses)


@settings.route("/settings/config/lead_status/new", methods=['GET', 'POST'])
@login_required
@is_admin
def config_lead_status_new():
    form = LeadStatusForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            max_order = db.session.query(db.func.max(LeadStatus.display_order)).scalar() or 0
            status = LeadStatus(
                status_name=form.status_name.data,
                is_active=form.is_active.data,
                display_order=max_order + 1
            )
            db.session.add(status)
            try:
                db.session.commit()
                flash('Lead status has been successfully created!', 'success')
                return redirect(url_for('settings.config_lead_statuses'))
            except IntegrityError:
                db.session.rollback()
                form.status_name.errors = ['A lead status with this name already exists.']
                flash('Failed to create lead status.', 'danger')
    return render_template("settings/config_lead_status_form.html",
                           title="New Lead Status", form=form)


@settings.route("/settings/config/lead_status/edit/<int:status_id>", methods=['GET', 'POST'])
@login_required
@is_admin
def config_lead_status_edit(status_id):
    status = LeadStatus.get_by_id(status_id)
    if not status:
        flash('Lead status not found.', 'danger')
        return redirect(url_for('settings.config_lead_statuses'))

    form = LeadStatusForm(exclude_id=status_id)
    if request.method == 'POST':
        if form.validate_on_submit():
            status.status_name = form.status_name.data
            status.is_active = form.is_active.data
            try:
                db.session.commit()
                flash('Lead status has been successfully updated!', 'success')
                return redirect(url_for('settings.config_lead_statuses'))
            except IntegrityError:
                db.session.rollback()
                form.status_name.errors = ['A lead status with this name already exists.']
                flash('Failed to update lead status.', 'danger')
    else:
        form.status_name.data = status.status_name
        form.is_active.data = status.is_active
    return render_template("settings/config_lead_status_form.html",
                           title="Edit Lead Status", form=form, status=status)


@settings.route("/settings/config/lead_status/del/<int:status_id>")
@login_required
@is_admin
def config_lead_status_delete(status_id):
    status = LeadStatus.get_by_id(status_id)
    if not status:
        flash('Lead status not found.', 'danger')
    elif status.leads:
        flash(f'Cannot delete \'{status.status_name}\': {len(status.leads)} lead(s) reference it. '
              'Please disable it instead.', 'warning')
    else:
        db.session.delete(status)
        db.session.commit()
        flash('Lead status has been removed.', 'success')
    return redirect(url_for('settings.config_lead_statuses'))


@settings.route("/settings/config/lead_status/move_up/<int:status_id>")
@login_required
@is_admin
def config_lead_status_move_up(status_id):
    _reorder_config_item(LeadStatus, status_id, direction='up')
    return redirect(url_for('settings.config_lead_statuses'))


@settings.route("/settings/config/lead_status/move_down/<int:status_id>")
@login_required
@is_admin
def config_lead_status_move_down(status_id):
    _reorder_config_item(LeadStatus, status_id, direction='down')
    return redirect(url_for('settings.config_lead_statuses'))


# ── Deal Stages ──

@settings.route("/settings/config/deal_stages")
@login_required
@is_admin
def config_deal_stages():
    stages = DealStage.deal_stage_query_all().all()
    return render_template("settings/config_deal_stages.html",
                           title="Deal Stages", stages=stages)


@settings.route("/settings/config/deal_stage/new", methods=['GET', 'POST'])
@login_required
@is_admin
def config_deal_stage_new():
    form = DealStageForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            max_order = db.session.query(db.func.max(DealStage.display_order)).scalar() or 0
            stage = DealStage(
                stage_name=form.stage_name.data,
                close_type=form.close_type.data.strip().lower() if form.close_type.data else None,
                is_active=form.is_active.data,
                display_order=max_order + 1
            )
            db.session.add(stage)
            try:
                db.session.commit()
                flash('Deal stage has been successfully created!', 'success')
                return redirect(url_for('settings.config_deal_stages'))
            except IntegrityError:
                db.session.rollback()
                form.stage_name.errors = ['A deal stage with this name already exists.']
                flash('Failed to create deal stage.', 'danger')
    return render_template("settings/config_deal_stage_form.html",
                           title="New Deal Stage", form=form)


@settings.route("/settings/config/deal_stage/edit/<int:stage_id>", methods=['GET', 'POST'])
@login_required
@is_admin
def config_deal_stage_edit(stage_id):
    stage = DealStage.get_deal_stage(stage_id)
    if not stage:
        flash('Deal stage not found.', 'danger')
        return redirect(url_for('settings.config_deal_stages'))

    form = DealStageForm(exclude_id=stage_id)
    if request.method == 'POST':
        if form.validate_on_submit():
            stage.stage_name = form.stage_name.data
            stage.close_type = form.close_type.data.strip().lower() if form.close_type.data else None
            stage.is_active = form.is_active.data
            try:
                db.session.commit()
                flash('Deal stage has been successfully updated!', 'success')
                return redirect(url_for('settings.config_deal_stages'))
            except IntegrityError:
                db.session.rollback()
                form.stage_name.errors = ['A deal stage with this name already exists.']
                flash('Failed to update deal stage.', 'danger')
    else:
        form.stage_name.data = stage.stage_name
        form.close_type.data = stage.close_type or ''
        form.is_active.data = stage.is_active
    return render_template("settings/config_deal_stage_form.html",
                           title="Edit Deal Stage", form=form, stage=stage)


@settings.route("/settings/config/deal_stage/del/<int:stage_id>")
@login_required
@is_admin
def config_deal_stage_delete(stage_id):
    stage = DealStage.get_deal_stage(stage_id)
    if not stage:
        flash('Deal stage not found.', 'danger')
    elif stage.deals:
        flash(f'Cannot delete \'{stage.stage_name}\': {len(stage.deals)} deal(s) reference it. '
              'Please disable it instead.', 'warning')
    else:
        db.session.delete(stage)
        db.session.commit()
        flash('Deal stage has been removed.', 'success')
    return redirect(url_for('settings.config_deal_stages'))


@settings.route("/settings/config/deal_stage/move_up/<int:stage_id>")
@login_required
@is_admin
def config_deal_stage_move_up(stage_id):
    _reorder_config_item(DealStage, stage_id, direction='up')
    return redirect(url_for('settings.config_deal_stages'))


@settings.route("/settings/config/deal_stage/move_down/<int:stage_id>")
@login_required
@is_admin
def config_deal_stage_move_down(stage_id):
    _reorder_config_item(DealStage, stage_id, direction='down')
    return redirect(url_for('settings.config_deal_stages'))


