from flask import Blueprint, redirect, render_template, request, logging, flash, abort, url_for
from flask_login import login_required, current_user
from wrapper_functions import roles_required
from forms import TransactionForm
from models import db, Transaction
from utils import recalculate_totals, автоматично_дефинирана_категория

transaction = Blueprint('transactions_blueprint', 'transaction')

@transaction.route('/add_transaction', methods=['GET', 'POST'])
@login_required
@roles_required('owner', 'admin')
def add_transaction():
    form = TransactionForm()
    if form.validate_on_submit():
        if 'file' in request.files:
            uploaded_file = request.files['file']
            print(f"File uploaded: {uploaded_file.filename}")
            logging.debug(f"File uploaded: {uploaded_file.filename}")
            if uploaded_file.filename != '':
                try:
                    # Processing CSV files
                    if uploaded_file.filename.endswith('.csv'):
                        print("Processing CSV file.")
                        logging.debug("Processing CSV file.")
                        import pandas as pd
                        data = pd.read_csv(uploaded_file)
                        for index, row in data.iterrows():
                            print(f"Adding transaction from row {index}: {row}")
                            transaction = Transaction(
                                date=row['date'],
                                type=row['type'],
                                category=row['category'],
                                debit=form.debit.data,
                                credit=form.credit.data,
                                amount=row['amount'],
                                description=row['description'],
                                account_id=current_user.accounts[0].id
                            )
                            db.session.add(transaction)
                        db.session.commit()
                        print("CSV file processed successfully!")
                        flash('File processed successfully!')
                        logging.info("CSV file processed successfully.")

                    # Processing Excel files (XLS and XLSX)
                    elif uploaded_file.filename.endswith(('.xls', '.xlsx')):
                        print("Processing Excel file.")
                        logging.debug("Processing Excel file.")
                        import pandas as pd
                        data = pd.read_excel(uploaded_file)
                        for index, row in data.iterrows():
                            print(f"Adding transaction from row {index}: {row}")
                            transaction = Transaction(
                                date=row['date'],
                                type=row['type'],
                                category=row['category'],
                                amount=row['amount'],
                                description=row['description'],
                                account_id=current_user.accounts[0].id
                            )
                            db.session.add(transaction)
                        db.session.commit()
                        print("Excel file processed successfully!")
                        flash('File processed successfully!')
                        logging.info("Excel file processed successfully.")

                    # Processing Word documents (DOC and DOCX)
                    elif uploaded_file.filename.endswith(('.doc', '.docx')):
                        print("Processing Word document.")
                        logging.debug("Processing Word document.")
                        from docx import Document
                        document = Document(uploaded_file)
                        for paragraph in document.paragraphs:
                            if paragraph.text:
                                fields = paragraph.text.split(',')
                                if len(fields) == 5:
                                    print(f"Adding transaction from paragraph: {fields}")
                                    transaction = Transaction(
                                        date=fields[0],
                                        type=fields[1],
                                        category=fields[2],
                                        amount=float(fields[3]),
                                        description=fields[4],
                                        account_id=current_user.accounts[0].id
                                    )
                                    db.session.add(transaction)
                        db.session.commit()
                        print("Word document processed successfully!")
                        flash('File processed successfully!')
                        logging.info("Word document processed successfully.")

                    else:
                        flash('Unsupported file format. Please upload a CSV, Excel, or Word file.')
                        logging.warning(f"Unsupported file format: {uploaded_file.filename}")

                except Exception as e:
                    db.session.rollback()
                    flash('Error processing the file: ' + str(e))
                    logging.error(f"Error processing the file: {e}")

        try:
            account = current_user.accounts[0]
            transaction = Transaction(
                date=form.date.data,
                type=form.type.data,
                category=form.category.data,
                debit=form.debit.data,  # Добавено поле за дебит
                credit=form.credit.data,  # Добавено поле за кредит
                income_statement_category=form.income_statement_category.data if form.income_statement_category.data else автоматично_дефинирана_категория(), # тук добавяме логиката
                amount=form.amount.data,
                description=form.description.data,
                account_id=account.id,
                user_id=current_user.id  # Тук добави това
            )
            db.session.add(transaction)
            db.session.commit()
            recalculate_totals()
            flash('Transaction added successfully!')
            logging.info("Transaction added successfully manually.")
            print("Calling the function before render_template for 'standard_dashboard.html'")
            return redirect(url_for('standard_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Error adding the transaction. Please try again. ' + str(e))
            logging.error(f"Error adding the transaction: {e}")
            print("Calling the function before render_template for 'add_transaction.html'")
    else:
        print(f"Form validation errors: {form.errors}")

    return render_template('add_transaction.html', form=form)


# Предишни рутове за транзакции
@transaction.route('/user_transactions', methods=['GET'])
@login_required
def view_user_transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    return render_template('transactions.html', transactions=transactions)

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

    flash('Транзакцията беше успешно изтрита.', 'success')
    return render_template('transactions.html', transactions=Transaction.query.filter_by(user_id=current_user.id).all())

