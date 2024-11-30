from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, jsonify, render_template, request, flash, redirect, url_for, flash, session, abort, send_file
from flask_sqlalchemy import SQLAlchemy
# from flask_mail import Mail, Message  # Commented out as emails are not used
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
# from models import Transaction, Category, db
from flask_babel import Babel, _
# from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature  # Commented out if tokens are not used
from functools import wraps
from datetime import datetime, date
# from sqlalchemy import func, extract  # Commented out if not using these functions
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
import base64
import logging  
import os
import re
from docx import Document
import base64

from utils import calculate_income_expense_data, calculate_liability_data, recalculate_totals, seed_categories,автоматично_дефинирана_категория,calculate_asset_data

from wtforms import FileField
from models import db, User, Account, Transaction, Category

from auth import auth_bp
# Initialize the app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Replace with your secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure Flask-Babel for bilingual support
app.config['BABEL_DEFAULT_LOCALE'] = 'bg'
app.config['BABEL_SUPPORTED_LOCALES'] = ['bg', 'en']

# Configure Babel
babel = Babel(app)

LANGUAGES = {
    'en': 'English',
    'bg': 'Bulgarian'
}
app.register_blueprint(auth_bp, url_prefix="/auth")



db.init_app(app)
migrate = Migrate(app, db)  # Add this line for migration initialization
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

with app.app_context():
    db.create_all()
    seed_categories()

import logging

# Configuring logging
logging.basicConfig(level=logging.DEBUG)

from transactions import transaction

app.register_blueprint(transaction)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from wrapper_functions import role_required, roles_required


### Context Processor for Current Year
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}


### Routes and Functions
@app.route('/')
@login_required
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        print("Calling function before render_template for 'index.html'")
        return render_template('index.html')


@app.route('/change_language/<language>')
@login_required
def change_language(language):
    if language in app.config['BABEL_SUPPORTED_LOCALES']:
        session['language'] = language
    return redirect(request.referrer or url_for('index'))

@app.route('/get_categories/<type>', methods=['GET'])
@login_required
def get_categories(type):
    categories = Category.query.filter_by(type=type).all()
    return jsonify([{"id": c.id, "name": c.name} for c in categories])


@app.route('/dashboard')
@login_required
def dashboard():
    # Logic based on the user's subscription plan
    if current_user.subscription_plan == "Standard":
        print("Calling the function before render_template for 'standard_dashboard.html'")
        return redirect(url_for('standard_dashboard'))
    elif current_user.subscription_plan == "Pro":
        print("Calling the function before render_template for 'pro_dashboard.html'")
        return render_template('pro_dashboard.html')
    elif current_user.subscription_plan == "Enterprise":
        print("Calling the function before render_template for 'enterprise_dashboard.html'")
        return render_template('enterprise_dashboard.html')
    elif current_user.subscription_plan == "Enterprise+":
        print("Calling the function before render_template for 'enterprise_plus_dashboard.html'")
        return render_template('enterprise_plus_dashboard.html')
    else:
        return "Unknown subscription plan"


@app.route('/standard_dashboard')
@login_required
def standard_dashboard():
    account = current_user.accounts[0]  # Assuming the user has one account
    print("Calling the function before render_template for 'standard_dashboard.html'")
    return render_template('standard_dashboard.html', account=account)


# Report Generation
@app.route('/generate_reports', methods=['GET'])
@login_required
def generate_reports():
    try:
        logging.debug("Starting report generation.")
        # Retrieving all transactions for the current user
        transactions = Transaction.query.filter_by(account_id=current_user.accounts[0].id).all()
        if not transactions:
            logging.warning("No transactions found for the current user.")
            flash(_('Not enough data available to generate reports.'))
            print("Calling function before rendering 'register.html'")
            return redirect(url_for('standard_dashboard'))
        logging.debug(f"Transactions found: {transactions}")
        
        # Example report - summing up income and expenses by month
        income = sum(t.amount for t in transactions if t.type == 'income')
        expense = sum(t.amount for t in transactions if t.type == 'expense')
        balance = income - expense
        logging.debug(f"Total Income: {income}, Total Expenses: {expense}, Balance: {balance}")
    except Exception as e:
        logging.error(f"Error while generating reports: {str(e)}")
        flash(_('An error occurred while generating the reports. Please try again.'))
        print("Calling function before rendering 'register.html'")
        return redirect(url_for('standard_dashboard'))

        # Additional logic for generating more reports can be added here


@app.route('/add_category', methods=['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        category_name = request.form.get('category_name')
        category_type = request.form.get('category_type')  # Типът на категорията (напр. разход/приход)
        
        # Логика за съхранение на новата категория в базата данни
        if category_name and category_type:
            new_category = Category(name=category_name, type=category_type)
            db.session.add(new_category)
            db.session.commit()
            flash('Category added successfully', 'success')
        else:
            flash('Please provide both a name and a type for the category.', 'error')
        
        return redirect(url_for('standard_dashboard'))

    return render_template('add_category.html')


@app.route('/balance_sheet')
def balance_sheet():
    # Извикай recalculate_totals(), за да се увериш, че всички стойности са актуални
    recalculate_totals()
    # Fetch data for balance sheet assets
    transactions = Transaction.query.filter_by(account_id=current_user.accounts[0].id).all()

    asset_data = calculate_asset_data(transactions)

    liability_data = calculate_liability_data(transactions)

    # Data validation checks for both assets and liabilities
    for key, value in {**asset_data, **liability_data}.items():
        if isinstance(value, (int, float)) and value < 0:
            flash(f"Invalid data: {key} cannot be negative.", 'error')
            
            print("Calling function before rendering 'balance_sheet_combined.html'")
    return render_template('balance_sheet_combined.html', assets=asset_data, liabilities=liability_data)



@app.route('/income_expense_statement')
def income_expense_statement():
    transactions = Transaction.query.filter_by(account_id=current_user.accounts[0].id).all()
    income_expense_data = calculate_income_expense_data(transactions)

    # Data validation checks
    for key, value in income_expense_data.items():
        if isinstance(value, (int, float)) and value < 0:
            flash(f"Invalid data: {key} cannot be negative.", 'error')

            print("Calling function before rendering 'income_expense_statement.html'")
        return render_template('income_expense_statement.html', **income_expense_data)


@app.route('/generate_report', methods=['GET'])
def generate_report():
    try:
        # Fetching all transactions of the current user
        transactions = Transaction.query.filter_by(account_id=current_user.accounts[0].id).all()

        income = sum(t.amount for t in transactions if t.type == 'income')
        expense = sum(t.amount for t in transactions if t.type == 'expense')
        balance = income - expense
        # Attempting to generate reports
        print("Calling function before render_template for 'reports.html'")
        return render_template(
            'reports.html',
            income=income,
            expense=expense,
            balance=balance,
        )
    except Exception as e:
        logging.error(f"Error while generating reports: {str(e)}")
        flash('An error occurred while generating the report. Please try again.' + str(e))
        print("Calling function before render_template for 'register.html'")
        return redirect(url_for('standard_dashboard'))


@app.route('/account_transactions_overview')
@login_required
@roles_required('owner', 'admin', 'user')
def view_account_transactions():
    account = current_user.accounts[0]
    transactions = Transaction.query.filter_by(account_id=account.id).order_by(Transaction.date.desc()).all()
    print("Calling function before render_template for 'reports.html'")
    return render_template('transactions.html', transactions=transactions)   


@app.route('/reports')
@login_required
def reports():
    all_reports_generated = True  # Flag to track whether all reports are successfully generated
    chart_url = None
    liabilities = []
    expense_breakdown = {}
    
    try:
        account = current_user.accounts[0]
        transactions = Transaction.query.filter_by(account_id=account.id).all()

        # Grouping transactions by category
        suppliers_liabilities = [transaction for transaction in transactions if transaction.category == 'Suppliers Liabilities']
        prepaid_revenue = [transaction for transaction in transactions if transaction.category == 'Prepaid Revenue']

        # Combine liabilities and prepaid revenues into a single list
        liabilities = suppliers_liabilities + prepaid_revenue

        # Sample report
        income = sum(t.amount for t in transactions if t.type == 'income')
        expenses = sum(t.amount for t in transactions if t.type == 'expense')
        profit = income - expenses

        # Calculate expenses by category
        for transaction in transactions:
            if transaction.type == 'expense':
                if transaction.category not in expense_breakdown:
                    expense_breakdown[transaction.category] = 0
                expense_breakdown[transaction.category] += transaction.amount

        # Adding new categories for expenses
        categories = []
        for category in categories:
            if category not in expense_breakdown:
                expense_breakdown[category] = 0

        # Month-to-Month Comparison
        data = [{
            'date': t.date,
            'type': t.type,
            'category': t.category,
            'amount': t.amount,
            'description': t.description
        } for t in transactions]

        df = pd.DataFrame(data)

        if not df.empty:
            df['month'] = pd.DatetimeIndex(df['date']).month
            current_month = datetime.now().month
            previous_month = current_month - 1 if current_month > 1 else 12

            income_current_month = df[(df['type'] == 'income') & (df['month'] == current_month)]['amount'].sum()
            income_previous_month = df[(df['type'] == 'income') & (df['month'] == previous_month)]['amount'].sum()

            # Financial Projections
            months = df['month'].nunique()
            average_monthly_profit = profit / months if months else 0
            projected_profit_next_three_months = average_monthly_profit * 3
        else:
            income_current_month = 0
            income_previous_month = 0
            projected_profit_next_three_months = 0
            all_reports_generated = False

        # KPIs
        kpis = {
            'Total Income': income,
            'Total Expenses': expenses,
            'Net Profit': profit,
            'Net Profit Margin': (profit / income * 100) if income else 0,
            'Gross Profit Margin': (profit / income * 100) if income else 0,
            'Net Profit Margin': (profit / income * 100) if income else 0,
            'Current Ratio': (income / expenses) if expenses else 0,
            'Quick Ratio': (income - df[df['category'] == 'Inventory']['amount'].sum()) / expenses if expenses else 0,
            'Inventory Turnover': (df[df['category'] == 'Cost of Goods Sold']['amount'].sum() / df[df['category'] == 'Inventory']['amount'].sum()) if df[df['category'] == 'Inventory']['amount'].sum() else 0,
            'Accounts Receivable Turnover': (income / df[df['category'] == 'Accounts Receivable']['amount'].sum()) if df[df['category'] == 'Accounts Receivable']['amount'].sum() else 0,
            'Working Capital': (income - expenses),
            'Days Payable Outstanding': (df[df['category'] == 'Accounts Payable']['amount'].sum() / (expenses / 30)) if expenses else 0,
            'Human Capital Value Added': profit / df[df['category'] == 'Employees']['amount'].sum() if df[df['category'] == 'Employees']['amount'].sum() else 0,
            'Operating Cash Flow': profit - df[df['category'] == 'Capital Expenditures']['amount'].sum() if df[df['category'] == 'Capital Expenditures']['amount'].sum() else profit
        }

        # Generating a chart for expenses by category
        img = io.BytesIO()
        if expense_breakdown:
            try:
                pd.Series(expense_breakdown).plot(kind='bar')
                plt.title('Expenses by Category')
                plt.xlabel('Categories')
                plt.ylabel('Amount')
                plt.tight_layout()
                plt.savefig(img, format='png')
                plt.close()
                img.seek(0)
                chart_url = base64.b64encode(img.getvalue()).decode()
            except Exception as e:
                print(f"Error generating the expense chart: {e}")
                all_reports_generated = False

    except Exception as e:
            print(f"Error executing report: {e}")
            flash('An error occurred while generating the reports.')
            all_reports_generated = False

    # Conditional rendering depending on successful report execution
    if all_reports_generated:
            return render_template('reports.html',
                                   liabilities=liabilities,
                                   income=income,
                                   expenses=expenses,
                                   profit=profit,
                                   expense_breakdown=expense_breakdown,
                                   income_current_month=income_current_month,
                                   income_previous_month=income_previous_month,
                                   projected_profit_next_three_months=projected_profit_next_three_months,
                                   kpis=kpis,
                                   chart_url=chart_url)
    else:
        flash('There were issues generating some of the reports.')
        
        kpis = {}  # или друга стойност по подразбиране, която има смисъл за твоя случай
        return render_template('reports.html',
                                   liabilities=liabilities,
                                   income=income,
                                   expenses=expenses,
                                   profit=profit,
                                   expense_breakdown=expense_breakdown,
                                   income_current_month=income_current_month,
                                   income_previous_month=income_previous_month,
                                   projected_profit_next_three_months=projected_profit_next_three_months,
                                   kpis=kpis,
                                   chart_url=chart_url)


# Route for generating and exporting income and expense reports
# @app.route('/export_report/<report_type>', methods=['GET'])
# @login_required
# def export_report(report_type):
#     transactions = Transaction.query.filter_by(account_id=current_user.accounts[0].id).all()
#     report_generated = False
#     exported_file = None

#     if not transactions:
#         flash(_('Not enough data to generate reports.'))
#     else:
#         if report_type == 'excel':
#             exported_file = export_to_excel(transactions)
#             report_generated = True
#         elif report_type == 'pdf':
#             exported_file = export_to_pdf(transactions)
#             report_generated = True
#         elif report_type == 'word':
#             exported_file = export_to_word(transactions)
#             report_generated = True
#         else:
#             flash(_('Unsupported report format.'))

#     if report_generated:
#         return exported_file
#     else:
#         flash(_('Unable to generate the report due to missing or incorrect data.'))
#         print("Calling the function before redirect.")
#         return redirect(url_for('generate_reports'))

    

# Error Handlers
@app.errorhandler(400)
def bad_request_error(error):
    flash('Bad request error occurred. Please check your input.', 'error')
    print("Redirecting to add_transaction for bad request.")
    return redirect(url_for('transactions_blueprint.add_transaction_manual'))  # Redirect to the add transaction page.

@app.errorhandler(403)
def forbidden_error(error):
    flash('Forbidden access error occurred.', 'error')
    print("Redirecting to a custom forbidden page.")
    return render_template('403.html'), 403  # Render a 403 error template.

@app.errorhandler(404)
def not_found_error(error):
    flash('Page not found.', 'error')
    print("Redirecting to a custom not found page.")
    return render_template('404.html'), 404  # Render a 404 error template.

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    flash('Internal server error occurred. Please try again.', 'error')
    print("Redirecting to standard dashboard for internal error.")
    return redirect(url_for('standard_dashboard'))  # Redirect to the dashboard.


if __name__ == '__main__':
    app.run(debug=True)
