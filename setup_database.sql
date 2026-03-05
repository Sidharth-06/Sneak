-- Create user and database for Company Insights Platform
CREATE USER "user" WITH PASSWORD 'password';
CREATE DATABASE insights_db OWNER "user";
ALTER USER "user" CREATEDB;
