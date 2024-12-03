from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date

db = SQLAlchemy()

association_table = db.Table(
    'association',
    db.Column('account_id', db.Integer, db.ForeignKey('account.id')),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'))
)


class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    users = db.relationship('User', secondary=association_table, back_populates='accounts')
    transactions = db.relationship('Transaction', backref='account', lazy=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    subscription_plan = db.Column(db.String(50), nullable=True, default="Standard")
    role = db.Column(db.String(20), default=None)  # 'owner', 'admin', 'user'
    accounts = db.relationship('Account', secondary=association_table, back_populates='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    category = db.Column(db.String(50), nullable=False)
    income_statement_category = db.Column(db.String(100), nullable=True)  # Категория в ОПР (напр. 'Personnel expenses')
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    debit = db.Column(db.String(100), nullable=True)  # New field for debit category
    credit = db.Column(db.String(100), nullable=True) 

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'

    # Model-level validation
    @staticmethod
    @db.validates('amount')
    def validate_amount(key, amount):
        if amount < 0:
            raise ValueError(_('Amount must be a positive number.'))
        return amount

