FROM python:3.7
RUN mkdir /app
ADD . /app
WORKDIR /app
RUN apt install gcc && \
    pip3 install -r requirements.txt
CMD ["python3", "app.py"]
