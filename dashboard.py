import secrets
from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response

from emailer import send_magic_link, send_email
from exceptions import NoSheetLink, NoAuthenticationToken, NoGroupID
from log import log
from storage import (
    create_user, get_user_by_email, get_user_by_id, get_all_users, user_count,
    delete_user, create_login_token, get_login_token, mark_token_used,
    create_session, get_session, delete_session, get_logs,
    get_schedule, get_sheet_link, get_group_id, get_token,
    save_schedule, save_sheet_link,
)

dashboard = Blueprint("dashboard", __name__, url_prefix="/dashboard",
                       template_folder="templates")


@dashboard.app_template_filter("timestamp")
def timestamp_filter(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def get_current_user():
    token = request.cookies.get("dashboard_session")
    if not token:
        return None
    session = get_session(token)
    if not session:
        return None
    user = get_user_by_id(session[1])
    return user


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return redirect(url_for("dashboard.login"))
        request.user = user
        return f(*args, **kwargs)
    return decorated


@dashboard.route("/login", methods=["GET", "POST"])
def login():
    has_users = user_count() > 0
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Please enter an email address.")
            return redirect(url_for("dashboard.login"))

        if not has_users:
            # First user signup
            user_id = create_user(email)
            token = secrets.token_urlsafe(32)
            create_login_token(email, token)
            try:
                send_magic_link(email, token)
                log("INFO", "dashboard", f"First user created: {email}")
            except Exception as e:
                log("ERROR", "dashboard", f"Failed to send magic link: {e}")
            flash("Check your email for a login link.")
        else:
            # Existing user login — always say "check email" to avoid enumeration
            user = get_user_by_email(email)
            if user:
                token = secrets.token_urlsafe(32)
                create_login_token(email, token)
                try:
                    send_magic_link(email, token)
                except Exception as e:
                    log("ERROR", "dashboard", f"Failed to send magic link: {e}")
            flash("If that email is registered, you'll receive a login link.")

        return redirect(url_for("dashboard.login"))

    return render_template("login.html", has_users=has_users)


@dashboard.route("/auth/<token>")
def auth(token):
    login_token = get_login_token(token)
    if not login_token:
        flash("Invalid or expired login link.")
        return redirect(url_for("dashboard.login"))

    email = login_token[1]
    mark_token_used(token)

    user = get_user_by_email(email)
    if not user:
        flash("No account found for this email.")
        return redirect(url_for("dashboard.login"))

    session_token = secrets.token_urlsafe(32)
    create_session(user[0], session_token)
    log("INFO", "dashboard", f"User logged in: {email}")

    response = make_response(redirect(url_for("dashboard.home")))
    response.set_cookie("dashboard_session", session_token,
                        httponly=True, samesite="Lax")
    return response


@dashboard.route("/logout")
def logout():
    token = request.cookies.get("dashboard_session")
    if token:
        delete_session(token)
    response = make_response(redirect(url_for("dashboard.login")))
    response.delete_cookie("dashboard_session")
    return response


@dashboard.route("/")
@login_required
def home():
    # Gather settings
    try:
        sheet_link = get_sheet_link()
    except NoSheetLink:
        sheet_link = None

    cron_schedule = get_schedule()

    try:
        group_id = get_group_id()
    except NoGroupID:
        group_id = None

    has_token = False
    try:
        get_token()
        has_token = True
    except NoAuthenticationToken:
        pass

    # Get upcoming events
    upcoming = []
    if sheet_link:
        try:
            from models.Sheet import Sheet
            sheet = Sheet.get_instance()
            events = sheet.upcoming_events(3)
            upcoming = [str(e) for e in events]
        except Exception as e:
            log("ERROR", "dashboard", f"Failed to load events: {e}")

    # Error count
    error_logs = get_logs(level="ERROR", limit=100)
    error_count = len(error_logs)

    return render_template("home.html",
                           sheet_link=sheet_link,
                           cron_schedule=cron_schedule,
                           group_id=group_id,
                           has_token=has_token,
                           upcoming=upcoming,
                           error_count=error_count,
                           user=request.user)


@dashboard.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_link":
            link = request.form.get("sheet_link", "").strip()
            if link:
                save_sheet_link(link)
                flash("Sheet link updated.")
                log("INFO", "dashboard", f"Sheet link updated by {request.user[1]}")

        elif action == "update_schedule":
            sched = request.form.get("schedule", "").strip()
            if sched:
                save_schedule(sched)
                flash("Schedule updated.")
                log("INFO", "dashboard", f"Schedule updated by {request.user[1]}")

        elif action == "test_email":
            try:
                send_email([request.user[1]], "Test Email",
                           "<p>This is a test email from the GroupMe Bot Dashboard.</p>")
                flash("Test email sent!")
            except Exception as e:
                flash(f"Failed to send test email: {e}")
                log("ERROR", "dashboard", f"Test email failed: {e}")

        return redirect(url_for("dashboard.settings"))

    try:
        sheet_link = get_sheet_link()
    except NoSheetLink:
        sheet_link = ""

    cron_schedule = get_schedule() or ""

    has_token = False
    try:
        get_token()
        has_token = True
    except NoAuthenticationToken:
        pass

    return render_template("settings.html",
                           sheet_link=sheet_link,
                           cron_schedule=cron_schedule,
                           has_token=has_token,
                           user=request.user)


@dashboard.route("/logs")
@login_required
def logs_page():
    level = request.args.get("level", "")
    log_entries = get_logs(level=level if level else None, limit=200)
    return render_template("logs.html",
                           logs=log_entries,
                           current_level=level,
                           user=request.user)


@dashboard.route("/users", methods=["GET", "POST"])
@login_required
def users():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "invite":
            email = request.form.get("email", "").strip().lower()
            if email:
                existing = get_user_by_email(email)
                if existing:
                    flash("A user with that email already exists.")
                else:
                    user_id = create_user(email)
                    token = secrets.token_urlsafe(32)
                    create_login_token(email, token)
                    try:
                        send_magic_link(email, token)
                        flash(f"Invite sent to {email}.")
                        log("INFO", "dashboard", f"User invited: {email} by {request.user[1]}")
                    except Exception as e:
                        flash(f"Failed to send invite: {e}")
                        log("ERROR", "dashboard", f"Failed to send invite to {email}: {e}")

        elif action == "remove":
            remove_id = request.form.get("user_id")
            if remove_id and int(remove_id) != request.user[0]:
                delete_user(int(remove_id))
                flash("User removed.")
                log("INFO", "dashboard", f"User removed (id={remove_id}) by {request.user[1]}")
            else:
                flash("You cannot remove yourself.")

        return redirect(url_for("dashboard.users"))

    all_users = get_all_users()
    return render_template("users.html",
                           all_users=all_users,
                           current_user_id=request.user[0],
                           user=request.user)
