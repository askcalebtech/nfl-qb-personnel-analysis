import logging
import argparse
import importlib
import time
import os
import sys

from pyspark.sql import SparkSession

logging.basicConfig(format='[%(levelname)s] [%(asctime)s] %(message)s', level=logging.INFO)
LOGGER = logging.getLogger()


def main():
    """Reads in command line arguments and calls the specified job

    Imports the module for a given job and acts as an entry point for the process

    :return: None
    """
    parser = argparse.ArgumentParser(description='Run a PySpark job')
    parser.add_argument('--job',
                        type=str,
                        required=True,
                        dest='job_name',
                        help="The name of the job module you want to run.")
    parser.add_argument('--add-py-files',
                        type=str,
                        required=False,
                        dest='py_file_location',
                        help="The py-files locations, temporary workaround (SSS-14703)")
    parser.add_argument('--job-args',
                        nargs='*',
                        help="Arguments to send to the PySpark job (example:--job-args tenant=:mill-int entity=:result")
    parser.add_argument('--local',
                        action="store_true",
                        help='Runs the job in local Spark Master')
    args = parser.parse_args()

    LOGGER.info("Called with arguments: %s", args)
    LOGGER.info('spark.%s', args.job_name)


    builder = SparkSession.builder
    builder = builder.appName("NFL-QB-Personnel-Analysis")
    if args.local:
        # Run spark locally with 4 workers threads (ideally, set this to the number of cores on your machine)
        builder = builder.master("local[4]").config("spark.driver.bindAddress", "localhost")

    with builder.getOrCreate() as spark:
        spark.sparkContext.addPyFile(args.py_file_location)
        # add jobs/jobs.zip directory to the $PYTHONPATH
        if os.path.exists('jobs.zip'):
            sys.path.insert(0, 'jobs.zip')
        else:
            sys.path.insert(0, './spark')


        job_module = importlib.import_module('spark.%s' % args.job_name)
        start = time.time()
        job_module.main(get_job_args(args), spark)
        end = time.time()

    LOGGER.info("\nExecution of job %s took %s seconds", args.job_name, (end - start))


def get_job_args(args):
    """Converts job arguments to key value pairs.

    :param args: job arguments from command line

    :return dictionary job_args: key value pairs for job arguments
    """
    job_args = dict()

    if args.job_args:
        job_args_tuples = [arg_str.split('=:') for arg_str in args.job_args]
        LOGGER.info('job_args_tuples: %s', job_args_tuples)
        job_args = {a[0]: a[1] for a in job_args_tuples}

    LOGGER.info("job_args are %s", job_args)
    LOGGER.info('\nRunning job %s...', args.job_name)

    return job_args


if __name__ == '__main__':
    main()
