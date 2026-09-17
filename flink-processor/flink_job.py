import os
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.table.expressions import col

def main():
    print("Starting flink job")
    #initialize streaming and table environments
    env = StreamExecutionEnvironment.get_execution_environment()
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    t_env = StreamTableEnvironment.create(env, settings)

    #connector location from dockerfile installation/ optional since flink automatically scans the flink/lib folder
    kafka_jar = "/opt/flink/lib/flink-sql-connector-kafka.jar"
    t_env.get_config().get_configuration().set_string("pipeline.jars", f"file://{kafka_jar}")
    
    #create table and map it to 'exchange_rates' kafka topic
    t_env.execute_sql("""
        CREATE TABLE fx_rates (
            firm STRING,
            currency STRING,
            buy DECIMAL(18, 8),
            sell DECIMAL(18, 8)
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'fx_rates',
            'properties.bootstrap.servers' = 'kafka:9092',
            'properties.group.id' = 'flink-forex-analyzer',
            'scan.startup.mode' = 'earliest-offset',
            'format' = 'json'
        )
    """)

    #simple print sink table to view results in stdout/logs to verify it is working
    t_env.execute_sql("""
    CREATE TABLE print_sink (
        firm STRING,
        currency STRING,
        buy DECIMAL(18, 8),
        sell DECIMAL(18, 8)
        ) WITH (
            'connector' = 'print' )
            """)
    
    fx_rates_table = t_env.from_path("fx_rates")
    table_result = fx_rates_table.execute_insert("print_sink")
    table_result.wait()
 
if __name__ == '__main__':
    main()