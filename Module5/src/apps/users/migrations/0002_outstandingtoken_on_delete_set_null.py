"""Make the DB-level FK match the ORM's on_delete=SET_NULL.

OutstandingToken.user is declared with on_delete=SET_NULL, but Django
never writes an ON DELETE clause into the actual database constraint --
that behavior is only enforced in Python when a User is deleted through
the ORM (e.g. the admin). Deleting a user row directly in SQL bypasses
Django entirely and hits the raw constraint, which has no ON DELETE
action and therefore blocks the delete. This adds it at the DB level too,
so a direct SQL delete behaves the same way an ORM delete already does.
"""

from django.db import migrations

CONSTRAINT = "token_blacklist_outstandingtoken_user_id_83bc629a_fk_users_id"

ADD_ON_DELETE_SET_NULL = f"""
    ALTER TABLE token_blacklist_outstandingtoken
        DROP CONSTRAINT {CONSTRAINT},
        ADD CONSTRAINT {CONSTRAINT}
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED;
"""

RESTORE_NO_ACTION = f"""
    ALTER TABLE token_blacklist_outstandingtoken
        DROP CONSTRAINT {CONSTRAINT},
        ADD CONSTRAINT {CONSTRAINT}
            FOREIGN KEY (user_id) REFERENCES users(id)
            DEFERRABLE INITIALLY DEFERRED;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
        ("token_blacklist", "0013_alter_blacklistedtoken_options_and_more"),
    ]

    operations = [
        migrations.RunSQL(sql=ADD_ON_DELETE_SET_NULL, reverse_sql=RESTORE_NO_ACTION),
    ]
