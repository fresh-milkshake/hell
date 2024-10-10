from datetime import datetime

import peewee as pw

from app.api.constants import INVITATION_EXPIRE_DELTA
from app.settings import DATABASE_PATH

handle = pw.SqliteDatabase(DATABASE_PATH)


class BaseModel(pw.Model):
    class Meta:
        database = handle


class Invitation(BaseModel):
    id = pw.IntegerField(primary_key=True)
    created_at = pw.DateTimeField(default=datetime.now)
    code = pw.CharField(max_length=32, unique=True)
    active = pw.BooleanField(default=True)
    used_at = pw.DateTimeField(null=True)
    expires_at = pw.DateTimeField(default=lambda: datetime.now() + INVITATION_EXPIRE_DELTA)


class APIKey(BaseModel):
    id = pw.IntegerField(primary_key=True)
    created_at = pw.DateTimeField(default=datetime.now)
    invitation = pw.ForeignKeyField(Invitation, backref='token', unique=True)
    token = pw.CharField(max_length=32, unique=True)
    active = pw.BooleanField(default=True)
    last_used = pw.DateTimeField(null=True)


Invitation.create_table()
APIKey.create_table()
