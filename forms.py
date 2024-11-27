# Import Flask-WTF and WTForms
from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, PasswordField, SubmitField, SelectField, FloatField, DateField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, NumberRange, Regexp
from wtforms import FileField
from models import User
### Forms

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8),
        Regexp(
            r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^\w\s]).+$',
            message='Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character.'
        )
    ])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('This username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('This email is already registered.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ManualTransactionForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()], format='%Y-%m-%d')
    type = SelectField('Type', choices=[('income', 'Income'), ('expense', 'Expense')], validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    income_statement_category = SelectField(
        'Income Statement Category',
        choices=[
            ('Raw materials, supplies, and external services expenses', 'Raw materials, supplies, and external services expenses'),
            ('Personnel expenses', 'Personnel expenses'),
            ('Depreciation and amortization expenses', 'Depreciation and amortization expenses'),
            ('Other expenses', 'Other expenses'),
            ('Tax expenses', 'Tax expenses'),
            ('Net sales revenue', 'Net sales revenue'),
            ('Other revenue', 'Other revenue'),
        ]
    )
    is_credit = BooleanField('Is Credit?')
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Add Transaction')


class FileUploadForm(FlaskForm):
    file = FileField('Upload File', validators=[DataRequired()])
    submit = SubmitField('Process File')
