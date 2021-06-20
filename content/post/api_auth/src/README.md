# Secure API authentication

- Install: `python3 -m venv venv && source venv/bin/activate && pip3 install -r requirements.txt`

- Run: `FLASK_ENV=development flask run`

- Test: `python3 -m unittest discover`

---

**This is a demo, not suitable for production.**

In a production build you might want to use:
- Database and an ORM (e.g. SQLAlchemy)
- Input validation (e.g. Cerberus)
- Slow password hashing (e.g. Bcrypt)
- WSGI application server (e.g. Gunicorn)
- Proxy server (e.g. Nginx)