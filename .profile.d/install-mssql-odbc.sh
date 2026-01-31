#!/bin/bash
# Install Microsoft ODBC Driver 18 for SQL Server on Heroku
set -e

echo "-----> Installing Microsoft ODBC Driver 18 for SQL Server"

# Add Microsoft repository
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Update apt and install driver
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18

# Install additional ODBC libraries
apt-get install -y unixodbc-dev

echo "-----> Microsoft ODBC Driver 18 installed successfully"
