# -*- coding: utf-8 -*-
"""
This module implements the CLI tool 'niddel' that can be used to interact with the Niddel Magnet
v2 API using magnetsdk2.
"""

import argparse
import json
import logging
from sys import stderr
from uuid import UUID

from magnetsdk2 import Connection
from magnetsdk2.iterator import FilePersistentAlertIterator
from magnetsdk2.validation import parse_date

logger = logging.getLogger('magnetsdk2')
handler = logging.StreamHandler(stderr)
handler.setFormatter(
    logging.Formatter('%(asctime)s pid=%(process)d %(module)s %(levelname)s %(message)s',
                      '%Y-%m-%dT%H:%M:%S%z'))
logger.addHandler(handler)


def main():
    # top-level parser
    parser = argparse.ArgumentParser(prog='niddel',
                                     description='Command-line utility to interact with the ' +
                                                 'Niddel Magnet v2 API')
    parser.add_argument("-p", "--profile",
                        help="which profile (from ~/.magnetsdk/config) to obtain API key from",
                        default='default')
    parser.add_argument("-i", "--indent", help="indent JSON output", action="store_const", const=4)
    parser.add_argument("-v", "--verbose", help="set verbose mode", action="store_true",
                        default=False)
    parser.set_defaults(indent=None)
    subparsers = parser.add_subparsers()

    # "me" command
    me_parser = subparsers.add_parser('me', help="display API key owner information",
                                      description="display API key owner information")
    me_parser.set_defaults(func=command_me)

    # "organizations" command
    org_parser = subparsers.add_parser('organizations',
                                       help="list basic organization information",
                                       description="list basic organization information")
    org_parser.add_argument("--id", help="get details on organization with the provided ID",
                            type=UUID, required=False)
    org_parser.set_defaults(func=command_organizations, id=None)

    # "alerts" command
    alerts_parser = subparsers.add_parser('alerts',
                                          help="list an organization's alerts",
                                          description="list an organization's alerts")
    alerts_parser.add_argument("organization", help="ID of the organization",
                               type=UUID)
    alerts_parser.add_argument("--start", help="initial batch date to process in YYYY-MM-DD format",
                               type=parse_arg_date)
    alerts_parser.add_argument("-p", "--persist",
                               help="file to store persistent state data, to ensure only alerts " +
                                    "that haven't been seen before are part of the output")
    alerts_parser.set_defaults(func=command_alerts, start=None, persist=None)

    # parse arguments, open connection and dispatch to proper function
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    conn = Connection(profile=args.profile)
    args.func(conn, args)


def parse_arg_date(value):
    try:
        return parse_date(value)
    except:
        raise argparse.ArgumentTypeError("unable to parse date, YYYY-MM-DD format expected")


def command_me(conn, args):
    print json.dumps(conn.get_me(), indent=args.indent)


def command_organizations(conn, args):
    if args.id:
        print json.dumps(conn.get_organization(args.id.__str__()), indent=args.indent)
    else:
        for organization in conn.iter_organizations():
            print json.dumps(organization, indent=args.indent)


def command_alerts(conn, args):
    if args.persist:
        iterator = FilePersistentAlertIterator(filename=args.persist, connection=conn,
                                               organization_id=args.organization.__str__(),
                                               start_date=args.start)
    else:
        iterator = conn.iter_organization_alerts(organization_id=args.organization.__str__(),
                                                 fromDate=args.start, sortBy='batchDate')
    for alert in iterator:
        print json.dumps(alert, indent=args.indent)

    if args.persist:
        iterator.save()


if __name__ == "__main__":
    main()
