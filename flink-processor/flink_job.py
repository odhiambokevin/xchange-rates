import os
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings

def main():
    print("Main flink job")
    #initialize streaming and table environments
    env = StreamExecutionEnvironment.get_execution_environment()
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, settings)

    #connector location from dockerfile installation/ optional since flink automatically scans the flink/lib folder
    kafka_jar = "/opt/flink/lib/flink-sql-connector-kafka.jar"
    t_env.get_config().get_configuration().set_string("pipeline.jars", f"file://{kafka_jar}")


    #create table and map it to 'exchange_rates' kafka topic
    #'currency' used for partitioning but json payload is processed
    t_env.execute_sql("""
        CREATE TABLE fx_rates (
            firm STRING,
            currency STRING,
            buy FLOAT,
            sell FLOAT,
            proctime AS PROCTIME() -- Processing time fallback for tracking engine state
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'exchange_rates',
            'properties.bootstrap.servers' = 'kafka:9092',
            'properties.group.id' = 'flink-forex-analyzer',
            'scan.startup.mode' = 'latest-offset',
            'format' = 'json'
        )
    """)

    #simple print sink tableto view results in stdout/logs to verify it is working
    t_env.execute_sql("""
        CREATE TABLE print_sink_data (
            currency STRING,
            best_buy_rate FLOAT,
            best_sell_rate FLOAT
        ) WITH (
            'connector' = 'print'
        )
    """)

    #tumbling 1 hour window so that flink discards previous state in case any of the pipeline scrapping fails
    #
    best_rates_table = t_env.sql_query("""
    SELECT 
        window_start,
        window_end,
        currency,
        MAX(buy) as best_buy_rate,
        MIN(sell) as best_sell_rate
    FROM TABLE(
        TUMBLE(TABLE fx_rates, DESCRIPTOR(proctime), INTERVAL '1' HOUR)
    )
    GROUP BY window_start, window_end, currency
    """)

    #push live table updates directly to the sink
    best_rates_table.execute_insert("print_sink_data")

if __name__ == '__main__':
    main()