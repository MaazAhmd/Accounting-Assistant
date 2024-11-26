from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from models import db, User,Account
from forms import RegistrationForm, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash



auth_bp = Blueprint('auth', __name__)



@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    print("Starting the register function")  # Print message when the function starts
    form = RegistrationForm()
    print("RegistrationForm object created")

    if form.validate_on_submit():
        print("Form is valid, proceeding to create user")  # Show if the form is validated successfully
        try:
            # Check how many users exist in the database
            if User.query.count() == 0:
                role = 'admin'  # The first user will be the admin
            else:
                role = 'user'  # All following users will be regular users
            new_user = User(
                username=form.username.data,
                email=form.email.data,
                role=role,  # Use the determined role here
                subscription_plan='Standard'  # Default subscription plan 'Standard'
            )
            new_user.set_password(form.password.data)
            new_user.confirmed = True  # Automatically confirm the user
            db.session.add(new_user)
            db.session.commit()
            print("User was successfully created")  # Confirm that the user was added

            # Create a new account and link it to the user
            account = Account(name=f"{new_user.username}'s Account")
            account.users.append(new_user)
            db.session.add(account)
            db.session.commit()
            print("Account was successfully created")  # Confirm that the account was added

            flash('Your account has been successfully created! Please log in.')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            print(f"An error occurred: {e}")  # Show error details if any occur
            flash('An error occurred while creating the account. Please try again.')
            print("Calling function before render_template for 'register.html'")
            return render_template('register.html', form=form)

    # If the form is not valid or it is a GET request
    print("Form is not valid or this is a GET request")
    print("Calling function before render_template for 'register.html'")
    return render_template('register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    print("Starting the login function")
    form = LoginForm()
    if form.validate_on_submit():
        print("Form is valid, attempting login")
        try:
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                print("User found and password is valid")
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                print("Invalid email or password")
                flash('Invalid email or password.')
        except Exception as e:
            print(f"An error occurred during login attempt: {e}")
            flash('An error occurred during login attempt. Please try again.')
            print("Calling function before render_template for 'login.html'")
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))
