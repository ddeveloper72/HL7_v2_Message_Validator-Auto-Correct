@echo off
echo Checking Heroku deployment status...
echo.
echo 1. Checking git remote:
git remote -v
echo.
echo 2. Checking last commit:
git log -1 --oneline
echo.
echo 3. Running schema update on Heroku:
heroku run python apply_report_details_schema.py
echo.
echo 4. Checking Heroku logs:
heroku logs --tail --num 20
