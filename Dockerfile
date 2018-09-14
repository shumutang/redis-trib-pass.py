FROM python:2
WORKDIR /dist
RUN pip install hiredis retrying Werkzeug click

ADD ./ /dist/
