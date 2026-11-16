# PUYO

PUYO is a Django application with student and owner accounts, role-specific
dashboards, and private profile management. Public registration creates student
accounts; owner accounts should be assigned by an administrator.

## Setup

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create a `.env` file in the repository root (next to `manage.py`) and set a
Django secret key and your Supabase PostgreSQL connection string:

```env
SECRET_KEY=<generated-secret>
DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres
```

Generate a key with
`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
Use the connection string provided by Supabase, replacing the placeholders with
your project values. Keep `.env` private; it is ignored by Git. The app loads
this file and requires SSL for `DATABASE_URL` connections. If `DATABASE_URL` is
not set, it uses the `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`POSTGRES_HOST`, and `POSTGRES_PORT` variables for a local PostgreSQL server.

Then apply migrations and start the development server:

```powershell
python manage.py migrate
python manage.py runserver
```

Create an administrator with `python manage.py createsuperuser`. Use the Django
admin site to assign the `Owner` role to an owner account.

## Tests

The test settings use an in-memory SQLite database only for automated tests;
the application settings continue to use PostgreSQL.

```powershell
python manage.py test --settings=PUYO.test_settings
```
