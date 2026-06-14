from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.fields.html5 import DateTimeLocalField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired, Optional
from wtforms_sqlalchemy.fields import QuerySelectField

from eeazycrm.users.models import User
from eeazycrm.leads.models import Lead
from eeazycrm.accounts.models import Account
from eeazycrm.contacts.models import Contact
from eeazycrm.deals.models import Deal
from eeazycrm.activities.models import ActivityType, ActivityStatus, Activity


class NewActivity(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired('Subject is mandatory')])
    activity_type = QuerySelectField('Activity Type',
                                     query_factory=ActivityType.activity_type_list_query,
                                     get_pk=lambda a: a.id,
                                     get_label=ActivityType.get_label,
                                     allow_blank=False,
                                     validators=[DataRequired(message='Please select activity type')])
    scheduled_date = DateTimeLocalField('Scheduled Date/Time',
                                        format='%Y-%m-%dT%H:%M',
                                        validators=[DataRequired('Scheduled date is required')])
    status = SelectField('Status',
                         choices=ActivityStatus.CHOICES,
                         default=ActivityStatus.PENDING,
                         validators=[DataRequired()])
    priority = SelectField('Priority',
                           choices=Activity.PRIORITY_CHOICES,
                           default='normal',
                           validators=[DataRequired()])
    leads = QuerySelectField('Lead',
                             query_factory=Lead.lead_list_query,
                             get_pk=lambda a: a.id,
                             get_label=Lead.get_label,
                             blank_text='-- Select Lead --',
                             allow_blank=True)
    accounts = QuerySelectField('Account',
                                query_factory=Account.account_list_query,
                                get_pk=lambda a: a.id,
                                get_label=Account.get_label,
                                blank_text='-- Select Account --',
                                allow_blank=True)
    contacts = QuerySelectField('Contact',
                                query_factory=Contact.contact_list_query,
                                get_pk=lambda a: a.id,
                                get_label=Contact.get_label,
                                blank_text='-- Select Contact --',
                                allow_blank=True)
    deals = QuerySelectField('Deal',
                             query_factory=Deal.deal_list_query,
                             get_pk=lambda a: a.id,
                             get_label=Deal.get_label,
                             blank_text='-- Select Deal --',
                             allow_blank=True)
    assignees = QuerySelectField('Assigned To',
                                 query_factory=User.user_list_query,
                                 get_pk=lambda a: a.id,
                                 get_label=User.get_label,
                                 default=User.get_current_user)
    description = StringField('Description', widget=TextArea())
    submit = SubmitField('Create Activity')


def filter_activity_status_query():
    return [
        {'id': 1, 'title': 'Pending'},
        {'id': 2, 'title': 'Completed'},
        {'id': 3, 'title': 'Cancelled'},
        {'id': 4, 'title': 'Overdue'},
    ]


def filter_activity_date_query():
    return [
        {'id': 1, 'title': 'Today'},
        {'id': 2, 'title': 'Next 7 Days'},
        {'id': 3, 'title': 'Next 30 Days'},
        {'id': 4, 'title': 'Overdue'},
        {'id': 5, 'title': 'Created Today'},
        {'id': 6, 'title': 'Created In Last 7 Days'},
    ]


class FilterActivities(FlaskForm):
    txt_search = StringField()
    activity_types = QuerySelectField(query_factory=ActivityType.activity_type_list_query,
                                      get_pk=lambda a: a.id,
                                      get_label=ActivityType.get_label,
                                      blank_text='[-- All Types --]',
                                      allow_blank=True)
    assignees = QuerySelectField(query_factory=User.user_list_query,
                                 get_pk=lambda a: a.id,
                                 get_label=User.get_label,
                                 allow_blank=True,
                                 blank_text='[-- All Owners --]')
    status_filter = SelectField(choices=[('', '[-- All Statuses --]')] +
                                        ActivityStatus.CHOICES +
                                        [('overdue', 'Overdue')],
                                validators=[Optional()])
    advanced_filter = QuerySelectField(query_factory=filter_activity_date_query,
                                       get_pk=lambda a: a['id'],
                                       get_label=lambda a: a['title'],
                                       allow_blank=True,
                                       blank_text='[-- Date Filter --]')
    submit = SubmitField('Filter Activities')
