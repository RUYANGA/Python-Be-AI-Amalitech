"""Make the DB-level FK match the ORM's on_delete=CASCADE.

URL.owner is declared with on_delete=CASCADE, but Django never writes an
ON DELETE clause into the actual database constraint -- that behavior is
only enforced in Python when a User is deleted through the ORM (e.g. the
admin). Deleting a user row directly in SQL bypasses Django entirely and
hits the raw constraint, which has no ON DELETE action and therefore
blocks the delete. This adds it at the DB level too, so a direct SQL
delete behaves the same way an ORM delete already does.
"""

from django.db import migrations

CONSTRAINT = "urls_owner_id_6825cb0f_fk_users_id"

ADD_ON_DELETE_CASCADE = f"""
    ALTER TABLE urls
        DROP CONSTRAINT {CONSTRAINT},
        ADD CONSTRAINT {CONSTRAINT}
            FOREIGN KEY (owner_id) REFERENCES users(id)
            ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED;
"""

RESTORE_NO_ACTION = f"""
    ALTER TABLE urls
        DROP CONSTRAINT {CONSTRAINT},
        ADD CONSTRAINT {CONSTRAINT}
            FOREIGN KEY (owner_id) REFERENCES users(id)
            DEFERRABLE INITIALLY DEFERRED;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("shortener", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(sql=ADD_ON_DELETE_CASCADE, reverse_sql=RESTORE_NO_ACTION),
    ]
