# Contributing Guide

This project is intentionally organized for first-time contributors and solo builders.

## Start here

1. Read `README.md`
2. Read `docs/README.md`
3. Read `docs/getting-started.md`
4. Run the app locally inside `nri_proj`
5. Run the tests before making changes

## Local setup

1. Create the virtual environment:
   `py -m venv nri_proj`
2. Activate it:
   `.\nri_proj\Scripts\Activate.ps1`
3. Install packages:
   `python -m pip install -r requirements.txt`
4. Copy env values:
   `Copy-Item .env.example .env`
5. Run migrations:
   `python manage.py migrate`
6. Run tests:
   `python manage.py test`
7. Start the API:
   `python manage.py run`

## Project layout in plain English

- `app/api`: HTTP routes
- `app/services`: business logic
- `app/models`: database models
- `app/schemas`: request and response shapes
- `app/repos`: reusable database queries
- `docs`: product and engineering documentation
- `tests`: unit, API, and integration coverage

## How to make safe changes

- Keep route handlers thin
- Put real behavior into services
- Update schemas when request or response shapes change
- Add or update tests with each behavior change
- Update docs whenever the feature, contract, or workflow changes

## Good first contribution ideas

- Add stronger validation rules
- Add more incident filters and list endpoints
- Add more device-health analytics
- Add example request payloads to docs
- Add a small frontend or admin dashboard

## Before publishing changes

- Run `python manage.py test`
- Check docs for anything that became outdated
- Keep commits focused and easy to read
