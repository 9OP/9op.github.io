Start flask server:

`FLASK_ENV=development flask run`

This is a demo, not suitable for production.

In a production build you might want to use:
- A database and an ORM (SQLAlchemy)
- Cerberus for input validation
- Bcrypt to hash and salt the passwords
- Gunicorn as WSGI application server
- Nginx as proxy server


Curl commands:

Signup:

curl -i \
    --header "Content-Type: application/json" \
    --request POST \
    --data '{ "email":"user@mail.com", "name": "user", "password":"123456" }' \
    http://localhost:5000/signup

Signin:

curl -i \
    --header "Content-Type: application/json" \
    --request POST \
    --data '{ "email":"user@mail.com", "password":"123456" }' \
    http://localhost:5000/signin

Whoami:

curl -i \
    --header "Authorization: Bearer 0cf91d94-2c35-40d4-9adc-bac12d10df0b" \
    --cookie "session=eyJ1c2VyIjoidXNlckBtYWlsLmNvbSJ9.YMXr_Q.suorZM3KeljhkcabYKlN4aRBw-s" \
    --request GET \
    http://localhost:5000/whoami


## Test

```python -m unittest discover```