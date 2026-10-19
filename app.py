from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable

from flask import Flask, jsonify, render_template, request, session
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from databases import Cigarette, User, db


VALID_ROLES = {'fumatore', 'sostenitore'}


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'change-this-secret-key'),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'DATABASE_URL',
            'sqlite:///quitstats.db',
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE') == '1',
        PERMANENT_SESSION_LIFETIME=timedelta(
            days=int(os.environ.get('SESSION_LIFETIME_DAYS', '30'))
        ),
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    register_routes(app)

    @app.get('/')
    def index() -> str:
        return render_template('index.html')

    @app.get('/health')
    def health() -> tuple[dict[str, str], int]:
        return {'status': 'ok'}, 200

    return app


def authenticated_user() -> User | None:
    user_id = session.get('user_id')
    if not isinstance(user_id, int):
        return None
    return db.session.get(User, user_id)


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if authenticated_user() is None:
            return jsonify(error='Autenticazione richiesta'), 401
        return view(*args, **kwargs)

    return wrapped


def role_required(role: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            user = authenticated_user()
            if user is None:
                return jsonify(error='Autenticazione richiesta'), 401
            if user.role != role:
                return jsonify(error='Operazione non consentita per questo ruolo'), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def user_payload(user: User) -> dict[str, Any]:
    return {
        'id': user.id,
        'username': user.username,
        'role': user.role,
        'friend_code': user.friend_code,
        'supported_user_id': user.supported_user_id,
    }


def stats_payload(user: User) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_month = start_of_day.replace(day=1)
    start_of_week = start_of_day - timedelta(days=start_of_day.weekday())
    query = Cigarette.query.filter(
        Cigarette.user_id == user.id,
        Cigarette.timestamp >= start_of_week,
    )
    weekly = query.with_entities(
        func.date(Cigarette.timestamp).label('day'),
        func.count(Cigarette.id).label('count'),
    ).group_by(func.date(Cigarette.timestamp)).all()
    weekly_total = sum(count for _, count in weekly)

    today = Cigarette.query.filter(
        Cigarette.user_id == user.id,
        Cigarette.timestamp >= start_of_day,
    ).order_by(Cigarette.timestamp.desc()).all()
    month = Cigarette.query.filter(
        Cigarette.user_id == user.id,
        Cigarette.timestamp >= start_of_month,
    ).count()
    total = Cigarette.query.filter_by(user_id=user.id).count()

    return {
        'today': len(today),
        'today_cigarettes': [
            {'id': cigarette.id, 'timestamp': cigarette.timestamp.isoformat()}
            for cigarette in today
        ],
        'month': month,
        'total': total,
        'weekly_total': weekly_total,
        'weekly_average': round(weekly_total / 7, 1),
        'weekly': [{'day': day, 'count': count} for day, count in weekly],
    }


def register_routes(app: Flask) -> None:
    @app.post('/api/auth/register')
    def register() -> Any:
        data = request.get_json(silent=True) or {}
        username = str(data.get('username', '')).strip()
        password = data.get('password')
        role = data.get('role', 'fumatore')

        if not username or not isinstance(password, str) or len(password) < 8:
            return jsonify(error='Username e password di almeno 8 caratteri sono obbligatori'), 400
        if role not in VALID_ROLES:
            return jsonify(error='Ruolo non valido'), 400
        if User.query.filter_by(username=username).first():
            return jsonify(error='Username già in uso'), 409

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role,
        )
        db.session.add(user)
        db.session.commit()
        session.clear()
        session.permanent = False
        session['user_id'] = user.id
        return jsonify(user=user_payload(user)), 201

    @app.post('/api/auth/login')
    def login() -> Any:
        data = request.get_json(silent=True) or {}
        username = str(data.get('username', '')).strip()
        password = data.get('password')
        user = User.query.filter_by(username=username).first()
        if user is None or not isinstance(password, str) or not check_password_hash(
            user.password_hash, password
        ):
            return jsonify(error='Credenziali non valide'), 401

        session.clear()
        session.permanent = bool(data.get('remember'))
        session['user_id'] = user.id
        return jsonify(user=user_payload(user))

    @app.post('/api/auth/logout')
    @login_required
    def logout() -> Any:
        session.clear()
        return jsonify(message='Logout effettuato')

    @app.get('/api/auth/me')
    @login_required
    def me() -> Any:
        return jsonify(user=user_payload(authenticated_user()))

    @app.post('/api/smoker/cigarettes')
    @role_required('fumatore')
    def add_cigarette() -> Any:
        user = authenticated_user()
        cigarette = Cigarette(user_id=user.id)
        db.session.add(cigarette)
        db.session.commit()
        return jsonify(cigarette_id=cigarette.id, stats=stats_payload(user)), 201

    @app.delete('/api/smoker/cigarettes/<int:cigarette_id>')
    @role_required('fumatore')
    def delete_cigarette(cigarette_id: int) -> Any:
        user = authenticated_user()
        cigarette = Cigarette.query.filter_by(
            id=cigarette_id,
            user_id=user.id,
        ).first()
        if cigarette is None:
            return jsonify(error='Sigaretta non trovata'), 404
        db.session.delete(cigarette)
        db.session.commit()
        return jsonify(stats=stats_payload(user))

    @app.get('/api/smoker/stats')
    @role_required('fumatore')
    def smoker_stats() -> Any:
        return jsonify(stats=stats_payload(authenticated_user()))

    @app.post('/api/smoker/friend-code')
    @role_required('fumatore')
    def friend_code() -> Any:
        user = authenticated_user()
        user.generate_friend_code()
        db.session.commit()
        return jsonify(friend_code=user.friend_code)

    @app.post('/api/supporter/connect')
    @login_required
    def connect_supporter() -> Any:
        data = request.get_json(silent=True) or {}
        code = str(data.get('friend_code', '')).strip().upper()
        smoker = User.query.filter_by(friend_code=code, role='fumatore').first()
        if smoker is None:
            return jsonify(error='Codice amico non valido'), 404

        user = authenticated_user()
        if smoker.id == user.id:
            return jsonify(error='Non puoi collegarti a te stesso'), 400
        user.supported_user_id = smoker.id
        db.session.commit()
        return jsonify(supported_user=user_payload(smoker))

    @app.get('/api/supporter/dashboard')
    @login_required
    def supporter_dashboard() -> Any:
        user = authenticated_user()
        if user.supported_user is None:
            return jsonify(supported_user=None, stats=None)
        return jsonify(
            supported_user=user_payload(user.supported_user),
            stats=stats_payload(user.supported_user),
        )


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5000')))
