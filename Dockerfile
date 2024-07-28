FROM ubuntu

RUN pip install -r requirements.txt

RUN python manage.py runserver