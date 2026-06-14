from datetime import datetime
from eeazycrm import db


class ActivityStatus:
    PENDING = 'pending'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
    ]

    DISPLAY = {
        PENDING: 'Pending',
        COMPLETED: 'Completed',
        CANCELLED: 'Cancelled',
    }

    CSS_CLASSES = {
        PENDING: 'badge-info',
        COMPLETED: 'badge-success',
        CANCELLED: 'badge-secondary',
        'overdue': 'badge-danger',
    }


class ActivityType(db.Model):
    __tablename__ = "activity_type"
    id = db.Column(db.Integer, db.Sequence('activity_type_id_seq'), primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50))

    activities = db.relationship('Activity', backref='activity_type', lazy=True)

    @staticmethod
    def activity_type_list_query():
        return ActivityType.query.order_by(ActivityType.name)

    @staticmethod
    def get_label(at):
        return at.display_name

    @staticmethod
    def get_by_id(activity_type_id):
        return ActivityType.query.filter_by(id=activity_type_id).first()

    @staticmethod
    def get_by_name(name):
        return ActivityType.query.filter_by(name=name).first()

    def __repr__(self):
        return f"ActivityType('{self.name}')"


class Activity(db.Model):
    __tablename__ = "activity"
    id = db.Column(db.Integer, db.Sequence('activity_id_seq'), primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    activity_type_id = db.Column(db.Integer, db.ForeignKey('activity_type.id'), nullable=False)
    description = db.Column(db.Text)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    completed_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default=ActivityStatus.PENDING)
    priority = db.Column(db.String(20), default='normal')

    lead_id = db.Column(db.Integer, db.ForeignKey('lead.id', ondelete='SET NULL'), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id', ondelete='SET NULL'), nullable=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contact.id', ondelete='SET NULL'), nullable=True)
    deal_id = db.Column(db.Integer, db.ForeignKey('deal.id', ondelete='SET NULL'), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'), nullable=True)

    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    owner = db.relationship('User', backref='activities', uselist=False, lazy=True)
    lead = db.relationship('Lead', backref='activities', uselist=False, lazy=True)
    account = db.relationship('Account', backref='activities', uselist=False, lazy=True)
    contact = db.relationship('Contact', backref='activities', uselist=False, lazy=True)
    deal = db.relationship('Deal', backref='activities', uselist=False, lazy=True)

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    PRIORITY_DISPLAY = {
        'low': 'Low',
        'normal': 'Normal',
        'high': 'High',
        'urgent': 'Urgent',
    }

    @property
    def is_overdue(self):
        if self.status in (ActivityStatus.COMPLETED, ActivityStatus.CANCELLED):
            return False
        return self.scheduled_date and self.scheduled_date < datetime.utcnow()

    @property
    def computed_status(self):
        if self.is_overdue and self.status == ActivityStatus.PENDING:
            return 'overdue'
        return self.status

    def get_status_display(self):
        if self.computed_status == 'overdue':
            return 'Overdue'
        return ActivityStatus.DISPLAY.get(self.status, 'Unknown')

    def get_status_css(self):
        return ActivityStatus.CSS_CLASSES.get(self.computed_status, 'badge-secondary')

    def get_priority_display(self):
        return self.PRIORITY_DISPLAY.get(self.priority, 'Normal')

    def get_related_entities(self):
        entities = []
        if self.lead:
            name = (self.lead.first_name or '') + ' ' + (self.lead.last_name or '')
            entities.append({'type': 'Lead', 'name': name.strip(), 'id': self.lead.id})
        if self.account:
            entities.append({'type': 'Account', 'name': self.account.name, 'id': self.account.id})
        if self.contact:
            name = (self.contact.first_name or '') + ' ' + (self.contact.last_name or '')
            entities.append({'type': 'Contact', 'name': name.strip(), 'id': self.contact.id})
        if self.deal:
            entities.append({'type': 'Deal', 'name': self.deal.title, 'id': self.deal.id})
        return entities

    def is_today(self):
        if not self.scheduled_date:
            return False
        return self.scheduled_date.date() == datetime.utcnow().date()

    @staticmethod
    def get_by_id(activity_id):
        return Activity.query.filter_by(id=activity_id).first()

    def __repr__(self):
        return f"Activity('{self.subject}', '{self.status}')"
