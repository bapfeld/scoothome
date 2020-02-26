import datetime, os
import psycopg2
import configparser, argparse

def initialize_params():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--ini_path',
        help="Path to the ini file",
        required=True,
    )
    return parser.parse_args()

def import_secrets(ini_path):
    """Simple script to parse config file"""
    config = configparser.ConfigParser()
    config.read(ini_path)
    return config['postgres']

def delete_records(pg, d):
    q = f"DELETE FROM predictions WHERE modified_date < '{d}'"
    with psycopg2.connect(pg['database'],
                          pg['username'],
                          pg['password'],
                          pg['port'],
                          pg['host']) as conn:
        with conn.cursor() as curs:
            conn.execute(q)
            conn.commit()

def main():
    args = initialize_params()
    pg = import_secrets(os.path.expanduser(args.ini_path))
    too_old = (datetime.datetime.now() - datetime.timedelta(weeks=2)).strftime("%Y-%m-%d %H:%M")
    delete_records(pg, too_old)

if __name__ == "__main__":
    main()
