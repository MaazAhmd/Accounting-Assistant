import os
from collections import defaultdict
from datetime import datetime
from io import BytesIO
import xlsxwriter
from flask import send_file
from docx import Document
import matplotlib.pyplot as plt
from models import Transaction, db,Category
from flask_login import current_user    




def seed_categories():
    asset_categories = [
        "Intangible Assets", "Fixed Assets", "Long-Term Financial Assets",
        "Deferred Taxes", "Inventory", "Receivables", "Receivables Over One Year",
        "Investments", "Cash", "Prepaid Expenses", "Unpaid Capital"
    ]

    liability_categories = [
        "Issued Capital", "Share Premiums", "Revaluation Reserve", "Reserves",
        "Retained Earnings", "Current Profit/Loss", "Provisions",
        "Liabilities Under One Year", "Liabilities Over One Year", "Deferred Income",
        "Liabilities Debit", "Liabilities Credit"
    ]

    # Add asset categories
    for category_name in asset_categories:
        if not Category.query.filter_by(name=category_name, type="income").first():
            db.session.add(Category(name=category_name, type="income"))

    # Add liability categories
    for category_name in liability_categories:
        if not Category.query.filter_by(name=category_name, type="expense").first():
            db.session.add(Category(name=category_name, type="expense"))

    db.session.commit()
    print("Categories seeded successfully.")



def автоматично_дефинирана_категория(transaction_description):
    # Проста логика за определяне на категорията на база описание
    if "заплата, salary" in transaction_description.lower() or "персонал, staff" in transaction_description.lower():
        return 'Personnel expenses'
    elif "материали, materials, supplies" in transaction_description.lower() or "доставки, supplies" in transaction_description.lower():
        return 'Raw materials, supplies, and external services expenses'
    elif "амортизация, depreciation" in transaction_description.lower():
        return 'Depreciation and amortization expenses'
    elif "данък, tax" in transaction_description.lower():
        return 'Tax expenses'
    elif "приход,revenue" in transaction_description.lower() or "продажба, sales, sale" in transaction_description.lower():
        return 'Net sales revenue'
    elif "друг приход, other income" in transaction_description.lower():
        return 'Other revenue'  # Добавена логика за другите приходи
    else:
        return 'Other expenses'  # Ако няма съвпадение, по подразбиране ще бъде 'Other expenses'

def recalculate_totals():
    # Извличане на всички транзакции на текущия потребител
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()

    # Пресмятане на общите суми за дебит и кредит
    asset_debit_total = 0.0
    asset_credit_total = 0.0
    liabilities_debit_total = 0.0
    liabilities_credit_total = 0.0

    for transaction in transactions:
        if transaction.debit:
            if transaction.category in ['Assets']:
                asset_debit_total += transaction.debit
            elif transaction.category in ['Liabilities']:
                liabilities_debit_total += transaction.debit

        if transaction.credit:
            if transaction.category in ['Assets']:
                asset_credit_total += transaction.credit
            elif transaction.category in ['Liabilities']:
                liabilities_credit_total += transaction.credit

    # Записване на стойностите в базата данни
    current_user.asset_debit_total = asset_debit_total
    current_user.asset_credit_total = asset_credit_total
    current_user.liabilities_debit_total = liabilities_debit_total
    current_user.liabilities_credit_total = liabilities_credit_total

    db.session.commit()
def calculate_income_expense_data(transactions):
    # Initialize the income_expense_data dictionary
    income_expense_data = defaultdict(float)

    # Get the current and previous year
    current_year = datetime.now().year
    previous_year = current_year - 1

    # Group transactions by category and year
    for transaction in transactions:
        year = transaction.date.year
        category = transaction.income_statement_category
        amount = transaction.amount

        if year == current_year:
            if category == "Raw materials, supplies, and external services expenses":
                income_expense_data["_3_raw_material_expenses_current"] += amount
            elif category == "Personnel expenses":
                income_expense_data["_4_personnel_expenses_current"] += amount
            elif category == "Depreciation and amortization expenses":
                income_expense_data["_5_depreciation_expenses_current"] += amount
            elif category == "Other expenses":
                income_expense_data["_6_other_expenses_current"] += amount
            elif category == "Tax expenses":
                income_expense_data["_7_tax_expenses_current"] += amount
            elif category == "Net sales revenue":
                income_expense_data["_1_net_sales_revenue_current"] += amount
            elif category == "Other revenue":
                income_expense_data["_2_other_revenue_current"] += amount

        elif year == previous_year:
            if category == "Raw materials, supplies, and external services expenses":
                income_expense_data["_3_raw_material_expenses_previous"] += amount
            elif category == "Personnel expenses":
                income_expense_data["_4_personnel_expenses_previous"] += amount
            elif category == "Depreciation and amortization expenses":
                income_expense_data["_5_depreciation_expenses_previous"] += amount
            elif category == "Other expenses":
                income_expense_data["_6_other_expenses_previous"] += amount
            elif category == "Tax expenses":
                income_expense_data["_7_tax_expenses_previous"] += amount
            elif category == "Net sales revenue":
                income_expense_data["_1_net_sales_revenue_previous"] += amount
            elif category == "Other revenue":
                income_expense_data["_2_other_revenue_previous"] += amount

    income_expense_data["_total_expenses_current"] = (
        income_expense_data["_3_raw_material_expenses_current"] +
        income_expense_data["_4_personnel_expenses_current"] +
        income_expense_data["_5_depreciation_expenses_current"] +
        income_expense_data["_6_other_expenses_current"]
    )
    income_expense_data["_total_expenses_previous"] = (
        income_expense_data["_3_raw_material_expenses_previous"] +
        income_expense_data["_4_personnel_expenses_previous"] +
        income_expense_data["_5_depreciation_expenses_previous"] +
        income_expense_data["_6_other_expenses_previous"]
    )
    income_expense_data["_total_revenue_current"] = (
        income_expense_data["_1_net_sales_revenue_current"] +
        income_expense_data["_2_other_revenue_current"]
    )
    income_expense_data["_total_revenue_previous"] = (
        income_expense_data["_1_net_sales_revenue_previous"] +
        income_expense_data["_2_other_revenue_previous"]
    )

    income_expense_data["_9_accounting_loss_current"] = max(
        0,
        income_expense_data["_total_expenses_current"] - income_expense_data["_total_revenue_current"]
    )
    income_expense_data["_9_accounting_loss_previous"] = max(
        0,
        income_expense_data["_total_expenses_previous"] - income_expense_data["_total_revenue_previous"]
    )

    income_expense_data["_10_net_profit_current"] = (
        income_expense_data["_8_accounting_profit_current"] -
        income_expense_data["_7_tax_expenses_current"]
    )
    income_expense_data["_10_net_profit_previous"] = (
        income_expense_data["_8_accounting_profit_previous"] -
        income_expense_data["_7_tax_expenses_previous"]
    )

    income_expense_data["_total_all_expenses_current"] = (
        income_expense_data["_total_expenses_current"] +
        income_expense_data["_7_tax_expenses_current"] +
        income_expense_data["_10_net_profit_current"]
    )
    income_expense_data["_total_all_expenses_previous"] = (
        income_expense_data["_total_expenses_previous"] +
        income_expense_data["_7_tax_expenses_previous"] +
        income_expense_data["_10_net_profit_previous"]
    )

    income_expense_data["_total_all_revenue_current"] = (
        income_expense_data["_total_revenue_current"] +
        income_expense_data["_11_total_loss_current"]
    )
    income_expense_data["_total_all_revenue_previous"] = (
        income_expense_data["_total_revenue_previous"] +
        income_expense_data["_11_total_loss_previous"]
    )

    return income_expense_data

def calculate_asset_data(transactions):
    # Initialize the asset_data dictionary
    asset_data = {
        'A_asset_unpaid_capital_current': 0,
        'A_asset_unpaid_capital_previous': 0,
        'B_intangible_assets_current': 0,
        'B_intangible_assets_previous': 0,
        'B_fixed_assets_current': 0,
        'B_fixed_assets_previous': 0,
        'B_long_term_financial_assets_current': 0,
        'B_long_term_financial_assets_previous': 0,
        'B_deferred_taxes_current': 0,
        'B_deferred_taxes_previous': 0,
        'B_total_noncurrent_assets_current': 0,
        'B_total_noncurrent_assets_previous': 0,
        'C_current_assets_current': 0,
        'C_current_assets_previous': 0,
        'C_inventory_current': 0,
        'C_inventory_previous': 0,
        'C_receivables_current': 0,
        'C_receivables_previous': 0,
        'C_receivables_over_one_year_current': 0,
        'C_receivables_over_one_year_previous': 0,
        'C_investments_current': 0,
        'C_investments_previous': 0,
        'C_cash_current': 0,
        'C_cash_previous': 0,
        'C_total_current_assets_current': 0,
        'C_total_current_assets_previous': 0,
        'D_prepaid_expenses_current': 0,
        'D_prepaid_expenses_previous': 0,
        'total_assets_current': 0,
        'total_assets_previous': 0,
    }

    # Get the current and previous year
    current_year = datetime.now().year
    previous_year = current_year - 1

    # Group transactions by category and year
    for transaction in transactions:
        year = transaction.date.year
        category = transaction.category
        amount = transaction.amount

        if year == current_year:
            if category == "Intangible Assets":
                asset_data['B_intangible_assets_current'] += amount
            elif category == "Fixed Assets":
                asset_data['B_fixed_assets_current'] += amount
            elif category == "Long-Term Financial Assets":
                asset_data['B_long_term_financial_assets_current'] += amount
            elif category == "Deferred Taxes":
                asset_data['B_deferred_taxes_current'] += amount
            elif category == "Inventory":
                asset_data['C_inventory_current'] += amount
            elif category == "Receivables":
                asset_data['C_receivables_current'] += amount
            elif category == "Receivables Over One Year":
                asset_data['C_receivables_over_one_year_current'] += amount
            elif category == "Investments":
                asset_data['C_investments_current'] += amount
            elif category == "Cash":
                asset_data['C_cash_current'] += amount
            elif category == "Prepaid Expenses":
                asset_data['D_prepaid_expenses_current'] += amount
            elif category == "Unpaid Capital":
                asset_data['A_asset_unpaid_capital_current'] += amount

        elif year == previous_year:
            if category == "Intangible Assets":
                asset_data['B_intangible_assets_previous'] += amount
            elif category == "Fixed Assets":
                asset_data['B_fixed_assets_previous'] += amount
            elif category == "Long-Term Financial Assets":
                asset_data['B_long_term_financial_assets_previous'] += amount
            elif category == "Deferred Taxes":
                asset_data['B_deferred_taxes_previous'] += amount
            elif category == "Inventory":
                asset_data['C_inventory_previous'] += amount
            elif category == "Receivables":
                asset_data['C_receivables_previous'] += amount
            elif category == "Receivables Over One Year":
                asset_data['C_receivables_over_one_year_previous'] += amount
            elif category == "Investments":
                asset_data['C_investments_previous'] += amount
            elif category == "Cash":
                asset_data['C_cash_previous'] += amount
            elif category == "Prepaid Expenses":
                asset_data['D_prepaid_expenses_previous'] += amount
            elif category == "Unpaid Capital":
                asset_data['A_asset_unpaid_capital_previous'] += amount

    # Calculate totals
    asset_data['B_total_noncurrent_assets_current'] = (
        asset_data['B_intangible_assets_current'] +
        asset_data['B_fixed_assets_current'] +
        asset_data['B_long_term_financial_assets_current'] +
        asset_data['B_deferred_taxes_current']
    )
    asset_data['B_total_noncurrent_assets_previous'] = (
        asset_data['B_intangible_assets_previous'] +
        asset_data['B_fixed_assets_previous'] +
        asset_data['B_long_term_financial_assets_previous'] +
        asset_data['B_deferred_taxes_previous']
    )
    asset_data['C_total_current_assets_current'] = (
        asset_data['C_inventory_current'] +
        asset_data['C_receivables_current'] +
        asset_data['C_receivables_over_one_year_current'] +
        asset_data['C_investments_current'] +
        asset_data['C_cash_current']
    )
    asset_data['C_total_current_assets_previous'] = (
        asset_data['C_inventory_previous'] +
        asset_data['C_receivables_previous'] +
        asset_data['C_receivables_over_one_year_previous'] +
        asset_data['C_investments_previous'] +
        asset_data['C_cash_previous']
    )
    asset_data['total_assets_current'] = (
        asset_data['A_asset_unpaid_capital_current'] +
        asset_data['B_total_noncurrent_assets_current'] +
        asset_data['C_total_current_assets_current'] +
        asset_data['D_prepaid_expenses_current']
    )
    asset_data['total_assets_previous'] = (
        asset_data['A_asset_unpaid_capital_previous'] +
        asset_data['B_total_noncurrent_assets_previous'] +
        asset_data['C_total_current_assets_previous'] +
        asset_data['D_prepaid_expenses_previous']
    )

    return asset_data



def calculate_liability_data(transactions):
    # Initialize the liability_data dictionary
    liability_data = {
        'A_equity_current': 0,
        'A_equity_previous': 0,
        'A_issued_capital_current': 0,
        'A_issued_capital_previous': 0,
        'A_share_premiums_current': 0,
        'A_share_premiums_previous': 0,
        'A_revaluation_reserve_current': 0,
        'A_revaluation_reserve_previous': 0,
        'A_reserves_current': 0,
        'A_reserves_previous': 0,
        'A_retained_earnings_current': 0,
        'A_retained_earnings_previous': 0,
        'A_current_profit_loss_current': 0,
        'A_current_profit_loss_previous': 0,
        'A_total_equity_current': 0,
        'A_total_equity_previous': 0,
        'B_provisions_current': 0,
        'B_provisions_previous': 0,
        'C_liabilities_one_year_current': 0,
        'C_liabilities_one_year_previous': 0,
        'C_liabilities_over_one_year_current': 0,
        'C_liabilities_over_one_year_previous': 0,
        'D_deferred_income_current': 0,
        'D_deferred_income_previous': 0,
        'total_liabilities_current': 0,
        'total_liabilities_previous': 0,
        'liabilities_credit_total': 0,
        'liabilities_debit_total': 0,
        'liabilities_credit_previous': 0,
        'liabilities_debit_previous': 0,
    }

    # Get the current and previous year
    current_year = datetime.now().year
    previous_year = current_year - 1

    # Group transactions by category and year
    for transaction in transactions:
        year = transaction.date.year
        category = transaction.category
        amount = transaction.amount

        if year == current_year:
            if category == "Issued Capital":
                liability_data['A_issued_capital_current'] += amount
            elif category == "Share Premiums":
                liability_data['A_share_premiums_current'] += amount
            elif category == "Revaluation Reserve":
                liability_data['A_revaluation_reserve_current'] += amount
            elif category == "Reserves":
                liability_data['A_reserves_current'] += amount
            elif category == "Retained Earnings":
                liability_data['A_retained_earnings_current'] += amount
            elif category == "Current Profit/Loss":
                liability_data['A_current_profit_loss_current'] += amount
            elif category == "Provisions":
                liability_data['B_provisions_current'] += amount
            elif category == "Liabilities Under One Year":
                liability_data['C_liabilities_one_year_current'] += amount
            elif category == "Liabilities Over One Year":
                liability_data['C_liabilities_over_one_year_current'] += amount
            elif category == "Deferred Income":
                liability_data['D_deferred_income_current'] += amount
            elif category == "Liabilities Debit":
                liability_data['liabilities_debit_total'] += amount
            elif category == "Liabilities Credit":
                liability_data['liabilities_credit_total'] += amount

        elif year == previous_year:
            if category == "Issued Capital":
                liability_data['A_issued_capital_previous'] += amount
            elif category == "Share Premiums":
                liability_data['A_share_premiums_previous'] += amount
            elif category == "Revaluation Reserve":
                liability_data['A_revaluation_reserve_previous'] += amount
            elif category == "Reserves":
                liability_data['A_reserves_previous'] += amount
            elif category == "Retained Earnings":
                liability_data['A_retained_earnings_previous'] += amount
            elif category == "Current Profit/Loss":
                liability_data['A_current_profit_loss_previous'] += amount
            elif category == "Provisions":
                liability_data['B_provisions_previous'] += amount
            elif category == "Liabilities Under One Year":
                liability_data['C_liabilities_one_year_previous'] += amount
            elif category == "Liabilities Over One Year":
                liability_data['C_liabilities_over_one_year_previous'] += amount
            elif category == "Deferred Income":
                liability_data['D_deferred_income_previous'] += amount
            elif category == "Liabilities Debit":
                liability_data['liabilities_debit_previous'] += amount
            elif category == "Liabilities Credit":
                liability_data['liabilities_credit_previous'] += amount

    # Calculate totals
    liability_data['A_total_equity_current'] = (
        liability_data['A_issued_capital_current'] +
        liability_data['A_share_premiums_current'] +
        liability_data['A_revaluation_reserve_current'] +
        liability_data['A_reserves_current'] +
        liability_data['A_retained_earnings_current'] +
        liability_data['A_current_profit_loss_current']
    )
    liability_data['A_total_equity_previous'] = (
        liability_data['A_issued_capital_previous'] +
        liability_data['A_share_premiums_previous'] +
        liability_data['A_revaluation_reserve_previous'] +
        liability_data['A_reserves_previous'] +
        liability_data['A_retained_earnings_previous'] +
        liability_data['A_current_profit_loss_previous']
    )
    liability_data['total_liabilities_current'] = (
        liability_data['A_total_equity_current'] +
        liability_data['B_provisions_current'] +
        liability_data['C_liabilities_one_year_current'] +
        liability_data['C_liabilities_over_one_year_current'] +
        liability_data['D_deferred_income_current']
    )
    liability_data['total_liabilities_previous'] = (
        liability_data['A_total_equity_previous'] +
        liability_data['B_provisions_previous'] +
        liability_data['C_liabilities_one_year_previous'] +
        liability_data['C_liabilities_over_one_year_previous'] +
        liability_data['D_deferred_income_previous']
    )

    

    return liability_data


# Export functions
def export_to_excel(transactions):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet()

    # Write headers
    headers = ['Date', 'Type', 'Category', 'Amount', 'Description']
    for col_num, header in enumerate(headers):
        worksheet.write(0, col_num, header)

    # Write transaction data
    for row_num, transaction in enumerate(transactions, start=1):
        worksheet.write(row_num, 0, transaction.date.strftime('%Y-%m-%d'))
        worksheet.write(row_num, 1, transaction.type)
        worksheet.write(row_num, 2, transaction.category)
        worksheet.write(row_num, 3, transaction.amount)
        worksheet.write(row_num, 4, transaction.description)

    workbook.close()
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='Income_Expense_Report.xlsx')

    

def export_to_pdf(transactions):
    # Generate PDF using matplotlib or reportlab
    output = BytesIO()
    plt.figure(figsize=(8, 6))
    categories = [t.category for t in transactions]
    amounts = [t.amount for t in transactions]
    plt.bar(categories, amounts)
    plt.title('Expenses by Category')
    plt.xlabel('Categories')
    plt.ylabel('Amount')
    plt.tight_layout()
    plt.savefig(output, format='pdf')
    output.seek(0)
    return send_file(output, mimetype='application/pdf', as_attachment=True, download_name='Income_Expense_Report.pdf')

    

def export_to_word(transactions):
    document = Document()
    document.add_heading('Income and Expense Report', level=1)
    table = document.add_table(rows=1, cols=5)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Date'
    hdr_cells[1].text = 'Type'
    hdr_cells[2].text = 'Category'
    hdr_cells[3].text = 'Amount'
    hdr_cells[4].text = 'Description'

    for transaction in transactions:
        row_cells = table.add_row().cells
        row_cells[0].text = transaction.date.strftime('%Y-%m-%d')
        row_cells[1].text = transaction.type
        row_cells[2].text = transaction.category
        row_cells[3].text = str(transaction.amount)
        row_cells[4].text = transaction.description

    output = BytesIO()
    document.save(output)
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                     as_attachment=True, download_name='Income_Expense_Report.docx')
