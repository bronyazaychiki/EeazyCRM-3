from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired, ValidationError

from eeazycrm.leads.models import LeadSource, LeadStatus
from eeazycrm.deals.models import DealStage


class LeadSourceForm(FlaskForm):
    source_name = StringField('Source Name', validators=[DataRequired(message='Source name is required')])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Lead Source')

    def __init__(self, *args, exclude_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.exclude_id = exclude_id

    def validate_source_name(self, source_name):
        query = LeadSource.query.filter_by(source_name=source_name.data)
        if self.exclude_id:
            query = query.filter(LeadSource.id != self.exclude_id)
        if query.first():
            raise ValidationError(f'Lead source \'{source_name.data}\' already exists.')


class LeadStatusForm(FlaskForm):
    status_name = StringField('Status Name', validators=[DataRequired(message='Status name is required')])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Lead Status')

    def __init__(self, *args, exclude_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.exclude_id = exclude_id

    def validate_status_name(self, status_name):
        query = LeadStatus.query.filter_by(status_name=status_name.data)
        if self.exclude_id:
            query = query.filter(LeadStatus.id != self.exclude_id)
        if query.first():
            raise ValidationError(f'Lead status \'{status_name.data}\' already exists.')


class DealStageForm(FlaskForm):
    stage_name = StringField('Stage Name', validators=[DataRequired(message='Stage name is required')])
    close_type = StringField('Close Type', description='Leave blank for open stages. Use "won" or "lost" for terminal stages.')
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save Deal Stage')

    def __init__(self, *args, exclude_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.exclude_id = exclude_id

    def validate_stage_name(self, stage_name):
        query = DealStage.query.filter_by(stage_name=stage_name.data)
        if self.exclude_id:
            query = query.filter(DealStage.id != self.exclude_id)
        if query.first():
            raise ValidationError(f'Deal stage \'{stage_name.data}\' already exists.')

    def validate_close_type(self, close_type):
        if close_type.data and close_type.data.strip().lower() not in ('won', 'lost'):
            raise ValidationError('Close type must be "won", "lost", or left blank.')
