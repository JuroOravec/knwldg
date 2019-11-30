import argparse
import csv
import datetime
import re


def event_id(event):
    def normalize(s):
        return re.sub(r'\W+', '', s.lower())

    return f'{normalize(event["name"])}__{normalize(event["city"])}__{event["start"]}'


def formatDate(dt: datetime.datetime):
    return dt.strftime('%Y-%m-%d')


def dateDuration(start, end):
    duration = (datetime.timedelta(days=1) + end - start)
    total_sec = duration.total_seconds()
    total_days = total_sec / (60 * 60 * 24)
    return total_days


def merge_csvs(inputs, output):
    '''
    Taken from https://stackoverflow.com/a/26599697/9788634
    '''

    # First determine the field names from the top line of each input file
    fieldnames = []
    for filename in inputs:
        with open(filename, "r", newline="") as f_in:
            reader = csv.reader(f_in)
            headers = next(reader)
            for h in headers:
                if h not in fieldnames:
                    fieldnames.append(h)

    # Then copy the data
    with open(output, "w", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        for filename in inputs:
            with open(filename, "r", newline="") as f_in:
                # Uses the field names in this file
                reader = csv.DictReader(f_in)
                for line in reader:
                    writer.writerow(line)


if __name__ == "__main__":
    # Run the util functions from command line

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", help='Choose a command')

    merge_parser = subparsers.add_parser('merge_csvs')
    merge_parser.add_argument("input", nargs="+",
                              help="name of the csv files to be merged")
    merge_parser.add_argument("-o", "--output", required=True,
                              help="name of the output file")
    args = parser.parse_args()

    if args.command == 'merge_csvs':
        merge_csvs(args.input, args.output)
