FROM python:3.11-slim

ARG UID=1000
ARG GID=1000

# RUN addgroup --gid $GID user-grp
# RUN adduser --uid $UID --gid $GID --disabled-password user

RUN apt-get update
RUN apt-get install poppler-utils -y

 

WORKDIR /opt/app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

USER $UID:$GID
CMD ["python", "./server.py"]
