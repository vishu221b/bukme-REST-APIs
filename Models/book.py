import mongoengine as meng
import datetime


class Book(meng.Document):
    name = meng.StringField(required=True, max_length=255)
    summary = meng.MultiLineStringField()
    author = meng.StringField(required=True)
    created_at = meng.DateTimeField(default=datetime.datetime.now)
    created_by = meng.EmailField(required=True)
    last_updated_at = meng.DateTimeField()
    last_updated_by = meng.EmailField(required=False)
    book_genre = meng.StringField(required=True)
    is_active = meng.BooleanField(default=True)

    meta = {
        'db_alias': 'bms_ent',
        'collection': 'books'
    }