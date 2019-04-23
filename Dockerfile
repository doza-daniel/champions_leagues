FROM python:latest

ADD . /code
WORKDIR /code

RUN pip install -r requirements.txt
RUN pip install uwsgi
RUN apt-get update && apt-get install -y nginx supervisor

RUN useradd --no-create-home nginx

RUN rm /etc/nginx/sites-enabled/default
RUN rm -r /root/.cache

COPY nginx.conf /etc/nginx/
COPY flask-site-nginx.conf /etc/nginx/conf.d/
COPY uwsgi.ini /etc/uwsgi/
COPY supervisord.conf /etc/

EXPOSE 5000

CMD ["/usr/bin/supervisord"]

