FROM flink:2.2-java17

ARG KAFKA_CONNECTOR_VERSION=5.0.0-2.2
ARG JDBC_CONNECTOR_VERSION=4.1.0-2.2

USER root

#python and pip if you haven't already for pyflink
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends python3 python3-pip python3-dev python3.12-venv wget && \
    rm -rf /var/lib/apt/lists/*

#pyflink requires python to point to python3
RUN ln -s /usr/bin/python3 /usr/bin/python

#create virtual environment to avoid error from PEP668 that prevents install into system python
RUN python3 -m venv /opt/venv

#make use of the virtual environment by default
ENV PATH="/opt/venv/bin:${PATH}"

#install pyflink library version matching flink version above exactly exactly
RUN pip install --no-cache-dir apache-flink==2.2.1

#downloading the exact kafka connector jar into flink dedicated library directory renamed using -o flag
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/${KAFKA_CONNECTOR_VERSION}/flink-sql-connector-kafka-${KAFKA_CONNECTOR_VERSION}.jar \
    -O /opt/flink/lib/flink-sql-connector-kafka.jar

#jdbc core
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc-core/${JDBC_CONNECTOR_VERSION}/flink-connector-jdbc-core-${JDBC_CONNECTOR_VERSION}.jar \
    -O /opt/flink/lib/flink-connector-jdbc-core-${JDBC_CONNECTOR_VERSION}.jar

#postgres jdbc connector
RUN wget https://repo1.maven.org/maven2/org/apache/flink/flink-connector-jdbc-postgres/${JDBC_CONNECTOR_VERSION}/flink-connector-jdbc-postgres-${JDBC_CONNECTOR_VERSION}.jar \
    -O /opt/flink/lib/flink-connector-jdbc-postgres-${JDBC_CONNECTOR_VERSION}.jar


#postgres jdbc driver
RUN wget https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.8/postgresql-42.7.8.jar \
    -O /opt/flink/lib/postgresql-42.7.8.jar

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
 
COPY flink_job.py wait-for-it.sh requirements.txt ./

RUN chmod +x wait-for-it.sh

#default to flink's user that is created by image
USER flink

#wait for flink port to be ready and then submit flink job to job manager
CMD ["sh", "-c", "./wait-for-it.sh -s -t 60 flink-jobmanager:8081 -- ./wait-for-it.sh -s -t 60 $KAFKA_SERVER -- flink run -m flink-jobmanager:8081 -py flink_job.py"]