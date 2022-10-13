FROM python:3-alpine

WORKDIR /app

RUN apk update && apk add mongodb-tools

RUN pip3 install pymongo python-gitlab

COPY ./gitlab_trace_to_mongo.py .

CMD [ "python3", "gitlab_trace_to_mongo.py"]
