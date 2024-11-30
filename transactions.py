from datetime import datetime
from flask import Blueprint, redirect, render_template, request, logging, flash, abort, url_for
from flask_login import login_required, current_user
from wrapper_functions import roles_required
from forms import ManualTransactionForm, FileUploadForm
from models import db, Transaction
from utils import export_balance_sheet_excel, export_balance_sheet_pdf, export_balance_sheet_word, export_income_expense_pdf, recalculate_totals, автоматично_дефинирана_категория, export_income_expense_word, export_income_expense_excel
import logging

transaction = Blueprint('transactions_blueprint', 'transaction')



# Configuring logging
logging.basicConfig(level=logging.DEBUG)



@transaction.route('/add_transaction_manual', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'admin')
def add_transaction_manual():
    form = ManualTransactionForm()  # Use a form specific to manual transactions
    if form.validate_on_submit():
        try:
            account = current_user.accounts[0]
            transaction = Transaction(
                date=form.date.data,
                type=form.type.data,
                category=form.category.data,
                is_credit=form.is_credit.data,
                income_statement_category=form.income_statement_category.data if form.income_statement_category.data else None,
                amount=form.amount.data,
                description=form.description.data,
                account_id=account.id,
                user_id=current_user.id
            )
            db.session.add(transaction)
            db.session.commit()
            recalculate_totals()
            flash('Transaction added successfully!')
            return redirect(url_for('standard_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding the transaction. Please try again. {e}')
    return render_template('add_transaction_manual.html', form=form)



@transaction.route('/add_transaction_file', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'admin')
def add_transaction_file():
    form = FileUploadForm()  # Use a form specific to file uploads
    if form.validate_on_submit():
        uploaded_file = request.files['file']
        if uploaded_file.filename.strip() == '':
            flash('Please upload a valid file.')
            return redirect(url_for('add_transaction_file'))

        try:
                    # Processing CSV files
                    if uploaded_file.filename.endswith('.csv'):
                        print("Processing CSV file.")
                        logging.debug("Processing CSV file.")
                        import pandas as pd
                        data = pd.read_csv(uploaded_file)

                        for index, row in data.iterrows():
                            print(f"Adding transaction from row {index}: {row}")
                            date_obj = datetime.strptime(row['date'], '%Y-%m-%d').date()
                            if( row.get('is_credit')==True):
                                is_credit = True
                            else:
                                 is_credit=False

                            transaction = Transaction(
                                date=date_obj,
                                type=row['type'],
                                category=row['category'],
                                is_credit=is_credit,

                                income_statement_category=row.get('income_statement_category', None),  # Default to None if missing
                                amount=row['amount'],
                                description=row['description'],
                                account_id=current_user.accounts[0].id,
                                user_id=current_user.id
                            )
                            db.session.add(transaction)
                        db.session.commit()
                        print("CSV file processed successfully!")
                        flash('File processed successfully!')
                        logging.info("CSV file processed successfully.")


                    elif uploaded_file.filename.endswith(('.xls', '.xlsx')):
                        print("Processing Excel file.")
                        logging.debug("Processing Excel file.")
                        import pandas as pd
                        data = pd.read_excel(uploaded_file)

                        for index, row in data.iterrows():
                            print(f"Adding transaction from row {index}: {row}")
                            date_obj = datetime.strptime(row['date'], '%Y-%m-%d').date()
                            if( row.get('is_credit')==True):
                                is_credit = True
                            else:
                                 is_credit=False
                            transaction = Transaction(
                                date=date_obj,
                                type=row['type'],
                                category=row['category'],
                                is_credit=is_credit,

                                income_statement_category=row.get('income_statement_category', None),  # Default to None if missing
                                amount=row['amount'],
                                description=row['description'],
                                account_id=current_user.accounts[0].id,
                                user_id=current_user.id
                            )
                            db.session.add(transaction)
                        db.session.commit()
                        print("Excel file processed successfully!")
                        flash('File processed successfully!')
                        logging.info("Excel file processed successfully.")

                    elif uploaded_file.filename.endswith(('.doc', '.docx')):
                        print("Processing Word document.")
                        logging.debug("Processing Word document.")
                        from docx import Document
                        document = Document(uploaded_file)

                        for paragraph in document.paragraphs:
                            if paragraph.text:
                                fields = paragraph.text.split(',')
                                date_obj = datetime.strptime(fields[0].strip(), '%Y-%m-%d').date()
                                if len(fields) == 7:  # Updated to expect all 7 fields in the paragraph
                                    print(f"Adding transaction from paragraph: {fields}")
                                    transaction = Transaction(
                                        date=date_obj,
                                        type=fields[1],
                                        category=fields[2],
                                        is_credit=fields[3].lower() == 'true',  # Convert 'is_credit' field to boolean
                                        income_statement_category=fields[4] if fields[4] else None,
                                        amount=float(fields[5]),
                                        description=fields[6],
                                        account_id=current_user.accounts[0].id,
                                        user_id=current_user.id
                                    )
                                    db.session.add(transaction)
                        db.session.commit()
                        print("Word document processed successfully!")
                        flash('File processed successfully!')
                        logging.info("Word document processed successfully.")


                    else:
                        flash('Unsupported file format. Please upload a CSV, Excel, or Word file.')
                        logging.warning(f"Unsupported file format: {uploaded_file.filename}")
                    return redirect(url_for('standard_dashboard'))

        except Exception as e:
                    db.session.rollback()
                    flash('Error processing the file: ' + str(e))
                    logging.error(f"Error processing the file: {e}")
    return render_template('add_transaction_file.html', form=form)


# @transaction.route('/add_transaction', methods=['GET', 'POST'])
# @login_required
# @roles_required('owner', 'admin')
# def add_transaction():

#     form = TransactionForm()
#     if form.validate_on_submit():
#         print(form.date.data, form.amount.data, form.type.data, form.category.data,"")
#         uploaded_file = request.files['file']
#         if uploaded_file.filename.strip() != '':
#             uploaded_file = request.files['file']
#             print(f"File uploaded: {uploaded_file.filename}")
#             logging.debug(f"File uploaded: {uploaded_file.filename}")
#             if uploaded_file.filename != '':
#                 try:
#                     # Processing CSV files
#                     if uploaded_file.filename.endswith('.csv'):
#                         print("Processing CSV file.")
#                         logging.debug("Processing CSV file.")
#                         import pandas as pd
#                         data = pd.read_csv(uploaded_file)
#                         for index, row in data.iterrows():
#                             print(f"Adding transaction from row {index}: {row}")
#                             transaction = Transaction(
#                                 date=row['date'],
#                                 type=row['type'],
#                                 category=row['category'],
#                                 is_credit=row.get('is_credit', False),  # Default to False if 'is_credit' is missing
#                                 income_statement_category=row.get('income_statement_category', None),  # Default to None if missing
#                                 amount=row['amount'],
#                                 description=row['description'],
#                                 account_id=current_user.accounts[0].id,
#                                 user_id=current_user.id
#                             )
#                             db.session.add(transaction)
#                         db.session.commit()
#                         print("CSV file processed successfully!")
#                         flash('File processed successfully!')
#                         logging.info("CSV file processed successfully.")


#                     elif uploaded_file.filename.endswith(('.xls', '.xlsx')):
#                         print("Processing Excel file.")
#                         logging.debug("Processing Excel file.")
#                         import pandas as pd
#                         data = pd.read_excel(uploaded_file)
#                         for index, row in data.iterrows():
#                             print(f"Adding transaction from row {index}: {row}")
#                             transaction = Transaction(
#                                 date=row['date'],
#                                 type=row['type'],
#                                 category=row['category'],
#                                 is_credit=row.get('is_credit', False),  # Default to False if 'is_credit' is missing
#                                 income_statement_category=row.get('income_statement_category', None),  # Default to None if missing
#                                 amount=row['amount'],
#                                 description=row['description'],
#                                 account_id=current_user.accounts[0].id,
#                                 user_id=current_user.id
#                             )
#                             db.session.add(transaction)
#                         db.session.commit()
#                         print("Excel file processed successfully!")
#                         flash('File processed successfully!')
#                         logging.info("Excel file processed successfully.")

#                     elif uploaded_file.filename.endswith(('.doc', '.docx')):
#                         print("Processing Word document.")
#                         logging.debug("Processing Word document.")
#                         from docx import Document
#                         document = Document(uploaded_file)
#                         for paragraph in document.paragraphs:
#                             if paragraph.text:
#                                 fields = paragraph.text.split(',')
#                                 if len(fields) == 7:  # Updated to expect all 7 fields in the paragraph
#                                     print(f"Adding transaction from paragraph: {fields}")
#                                     transaction = Transaction(
#                                         date=fields[0],
#                                         type=fields[1],
#                                         category=fields[2],
#                                         is_credit=fields[3].lower() == 'true',  # Convert 'is_credit' field to boolean
#                                         income_statement_category=fields[4] if fields[4] else None,
#                                         amount=float(fields[5]),
#                                         description=fields[6],
#                                         account_id=current_user.accounts[0].id,
#                                         user_id=current_user.id
#                                     )
#                                     db.session.add(transaction)
#                         db.session.commit()
#                         print("Word document processed successfully!")
#                         flash('File processed successfully!')
#                         logging.info("Word document processed successfully.")


#                     else:
#                         flash('Unsupported file format. Please upload a CSV, Excel, or Word file.')
#                         logging.warning(f"Unsupported file format: {uploaded_file.filename}")
#                     return redirect(url_for('standard_dashboard'))

#                 except Exception as e:
#                     db.session.rollback()
#                     flash('Error processing the file: ' + str(e))
#                     logging.error(f"Error processing the file: {e}")
#         elif form.date.data and form.amount.data and form.type.data and form.category.data:
#             print("Adding transaction manually.")	
#             try:
#                 account = current_user.accounts[0]
#                 transaction = Transaction(
#                     date=form.date.data,
#                     type=form.type.data,
#                     category=form.category.data,
#                     is_credit=form.is_credit.data,
#                     income_statement_category=form.income_statement_category.data if form.income_statement_category.data else автоматично_дефинирана_категория(), # тук добавяме логиката
#                     amount=form.amount.data,
#                     description=form.description.data,
#                     account_id=account.id,
#                     user_id=current_user.id  
#                 )
#                 db.session.add(transaction)
#                 db.session.commit()
#                 recalculate_totals()
#                 flash('Transaction added successfully!')
#                 logging.info("Transaction added successfully manually.")
#                 print("Calling the function before render_template for 'standard_dashboard.html'")
#                 return redirect(url_for('standard_dashboard'))
#             except Exception as e:
#                 db.session.rollback()
#                 flash('Error adding the transaction. Please try again. ' + str(e))
#                 logging.error(f"Error adding the transaction: {e}")
#                 print("Calling the function before render_template for 'add_transaction.html'")
#     else:
#         print(f"Form validation errors: {form.errors}")
#         print(f"Form validation errors: {form.errors}")

#     return render_template('add_transaction.html', form=form)


# Предишни рутове за транзакции
@transaction.route('/user_transactions', methods=['GET'])
@login_required
def view_user_transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    return render_template('transactions.html', transactions=transactions)


@transaction.route('/generate_general_ledger', methods=['POST'])
@login_required
def generate_general_ledger():
    # Fetch all transactions for the current user
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()

    # Create a summary of debits and credits
    general_ledger = {}
    for t in transactions:
        category = t.category
        if category not in general_ledger:
            general_ledger[category] = {'debit': 0, 'credit': 0}

        if t.is_credit:
            general_ledger[category]['credit'] += t.amount
        else:
            general_ledger[category]['debit'] += t.amount

    return render_template(
        'general_ledger.html',
        general_ledger=general_ledger,
        transactions=transactions
    )


# Тук добави новия рут за изтриване на транзакция
@transaction.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Проверка дали транзакцията принадлежи на текущия потребител (ако е необходимо)
    if transaction.user_id != current_user.id:
        abort(403)

    # Изтриване на транзакцията
    db.session.delete(transaction)
    db.session.commit()
    
    # Актуализиране на общите стойности след изтриване
    recalculate_totals()

    flash('Transaction successfully deleted.', 'success')
    return render_template('transactions.html', transactions=Transaction.query.filter_by(user_id=current_user.id).all())


@transaction.route('/export_income_expense/<string:type>')
@login_required
def export_income_expense(type):
    """
    Exports the income and expense statement in the format specified by `type`.
    """
    if type == 'pdf':
        return export_income_expense_pdf()
    elif type == 'word':
        return export_income_expense_word()
    elif type == 'excel':
        return export_income_expense_excel()
    else:
        return "Invalid export type. Use 'pdf', 'word', or 'excel'.", 400

@transaction.route('/export_balance_sheet', methods=['GET'])
def export_balance_sheet():
    export_type = request.args.get('type')
    if export_type == 'pdf':
        return export_balance_sheet_pdf()
    elif export_type == 'word':
        return export_balance_sheet_word()
    elif export_type == 'excel':
        return export_balance_sheet_excel()
    else:
        return "Invalid export type", 400