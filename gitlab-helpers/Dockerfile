FROM python:3-slim-buster

WORKDIR /app

RUN pip3 install pymongo python-gitlab

COPY ./gitlab-trace-to-mongo.py .

CMD [ "python3", "gitlab-trace-to-mongo.py"]