# -*- coding: utf-8 -*-
"""
This module implements the CLI tool 'niddel' that can be used to interact with the Niddel Magnet
v2 API using magnetsdk2.
"""

import argparse
import json
import logging
from sys import stdout, stderr
from uuid import UUID
from os import linesep
from codecs import BOM_UTF8

from magnetsdk2 import Connection
from magnetsdk2.cef import convert_alert
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
    parser.add_argument("-o", "--outfile",
                        help="destination file to write to, if exists will be overwritten",
                        type=argparse.FileType('wb'), default=stdout)
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
    alerts_parser.add_argument("-f", "--format", choices=['json', 'cef'], default='json',
                               help="format in which to output alerts")
    alerts_parser.set_defaults(func=command_alerts, start=None, persist=None)

    # parse arguments, open connection and dispatch to proper function
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    conn = Connection(profile=args.profile)
    args.func(conn, args)
    if args.outfile != stdout:
        args.outfile.close()


def parse_arg_date(value):
    try:
        return parse_date(value)
    except:
        raise argparse.ArgumentTypeError("unable to parse date, YYYY-MM-DD format expected")


def command_me(conn, args):
    json.dump(args.outfile, conn.get_me(), indent=args.indent)


def command_organizations(conn, args):
    if args.id:
        json.dump(args.outfile, conn.get_organization(args.id.__str__()), indent=args.indent)
    else:
        for organization in conn.iter_organizations():
            args.outfile.write(json.dumps(organization, indent=args.indent))
            args.outfile.write(linesep)


def command_alerts(conn, args):
    if args.persist:
        iterator = FilePersistentAlertIterator(filename=args.persist, connection=conn,
                                               organization_id=args.organization.__str__(),
                                               start_date=args.start)
    else:
        iterator = conn.iter_organization_alerts(organization_id=args.organization.__str__(),
                                                 fromDate=args.start, sortBy='batchDate')

    if args.outfile != stdout and args.format == 'cef':
        args.outfile.write(BOM_UTF8)

    for alert in iterator:
        if args.format == 'json':
            json.dump(args.outfile, alert, indent=args.indent)
        elif args.format == 'cef':
            convert_alert(args.outfile, alert, args.organization.__str__())
        args.outfile.write(linesep)

    if args.persist:
        iterator.save()


if __name__ == "__main__":
    main()
