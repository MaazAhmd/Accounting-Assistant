from datetime import datetime
from flask import Blueprint, redirect, render_template, request, logging, flash, abort, url_for
from flask_login import login_required, current_user
from wrapper_functions import roles_required
from forms import ManualTransactionForm, FileUploadForm
from models import db, Transaction
from utils import export_balance_sheet_excel, export_balance_sheet_pdf, export_balance_sheet_word, export_income_expense_pdf, recalculate_totals, автоматично_дефинирана_категория, export_income_expense_word, export_income_expense_excel
import logging
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
import io



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
                credit=form.credit.data,
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
                     

                            transaction = Transaction(
                                date=date_obj,
                                type=row['type'],
                                category=row['category'],
                                debit = str(row.get('Debit', '')).strip() if pd.notna(row.get('Debit')) else None,
                                credit = str(row.get('Credit', '')).strip() if pd.notna(row.get('Credit')) else None,
                                income_statement_category=row.get('Income Statement', None),  # Default to None if missing
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
                      
                            transaction = Transaction(
                                date=row['date'],
                                type=row['type'],
                                category=row['category'],
                                debit = str(row.get('Debit', '')).strip() if pd.notna(row.get('Debit')) else None,
                                credit = str(row.get('Credit', '')).strip() if pd.notna(row.get('Credit')) else None,
                                income_statement_category=str(row.get('Income Statement', '')).strip() if pd.notna(row.get('Income Statement')) else None,
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
                                print(f"Adding transaction from paragraph: {fields}")
                                transaction = Transaction(
                                        date=date_obj,
                                        type=fields[1],
                                        category=fields[2],
                                        debit=fields[3].strip() or None,  # Debit field
                                        credit=fields[4].strip() or None,  # Credit field
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

        if t.credit:
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
    




from flask import send_file, Response
from io import BytesIO
import pandas as pd

# Route for exporting to Excel
@transaction.route('/export_general_ledger_excel', methods=['GET'])
@login_required
def export_general_ledger_excel():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    
    # Create a DataFrame for the transactions
    data = [
        {
            'Date': t.date.strftime('%Y-%m-%d'),
            'Type': 'Income' if t.type == 'income' else 'Expense',
            'Category': t.category,
            'Amount': t.amount,
            'Debit': t.debit if t.debit else 'N/A',
            'Credit': t.credit if t.credit else 'N/A',
            'Description': t.description
        }
        for t in transactions
    ]
    df = pd.DataFrame(data)

    # Save to an Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='General Ledger')
    output.seek(0)

    # Serve the file
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='general_ledger.xlsx')

@transaction.route('/export_general_ledger_pdf', methods=['GET'])
@login_required
def export_general_ledger_pdf():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()

    # Prepare the PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    normal_style = styles["Normal"]
    table_header_style = styles["Heading4"]

    # Add Title
    elements.append(Paragraph("General Ledger", title_style))
    elements.append(Spacer(1, 12))

    # Prepare table data
    table_data = [
        ["Date", "Type", "Category", "Amount", "Debit", "Credit", "Description"]
    ]

    # Truncate long text fields to avoid overflow
    def truncate_text(text, max_length):
        return text if len(text) <= max_length else text[:max_length - 3] + "..."

    # Add transactions to table
    for t in transactions:
        table_data.append([
            t.date.strftime('%Y-%m-%d'),
            "Income" if t.type == "income" else "Expense",
            truncate_text(t.category, 15),  # Limit category to 15 characters
            f"{t.amount:.2f}",
            truncate_text(t.debit, 20) if t.debit else "N/A",
            truncate_text(t.credit, 20) if t.credit else "N/A",
            truncate_text(t.description or "N/A", 30)  # Limit description to 30 characters
        ])

    # Adjust column widths
    table = Table(table_data, colWidths=[50, 35, 80, 50, 100, 100, 140])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # Reduce font size to fit content
    ]))

    # Add table to the PDF
    elements.append(table)

    # Build PDF
    doc.build(elements)

    # Serve the PDF
    buffer.seek(0)
    return send_file(buffer, mimetype='application/pdf',
                     as_attachment=True, download_name='general_ledger.pdf')
