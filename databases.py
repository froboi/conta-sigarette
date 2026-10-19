from datetime import datetime, timezone
import secrets
import string

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import CheckConstraint, Index

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        CheckConstraint(
            "role IN ('fumatore', 'sostenitore')",
            name='ck_users_role',
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='fumatore')
    friend_code = db.Column(db.String(6), unique=True, nullable=True)
    supported_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
    )

    cigarettes = db.relationship(
        'Cigarette',
        back_populates='user',
        cascade='all, delete-orphan',
    )
    supported_user = db.relationship(
        'User',
        remote_side=[id],
        back_populates='supporters',
        foreign_keys=[supported_user_id],
    )
    supporters = db.relationship(
        'User',
        back_populates='supported_user',
        foreign_keys=[supported_user_id],
    )

    def generate_friend_code(self) -> str:
        if self.role == 'fumatore' and not self.friend_code:
            self.friend_code = secrets.choice(
                string.ascii_uppercase + string.digits
            )
            self.friend_code += ''.join(
                secrets.choice(string.ascii_uppercase + string.digits)
                for _ in range(5)
            )
        return self.friend_code

class Cigarette(db.Model):
    __tablename__ = 'cigarettes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    user = db.relationship('User', back_populates='cigarettes')


Index('ix_cigarettes_user_timestamp', Cigarette.user_id, Cigarette.timestamp)