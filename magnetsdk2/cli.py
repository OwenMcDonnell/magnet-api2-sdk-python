# -*- coding: utf-8 -*-
"""
This module implements the CLI tool 'niddel' that can be used to interact with the Niddel Magnet
v2 API using magnetsdk2.
"""

import argparse
import json
import logging
from codecs import BOM_UTF8
from datetime import datetime
from errno import EPIPE
from glob import glob
from os import linesep, sep
from os.path import expanduser, join, basename, isfile
from sys import stdout, stderr, exc_info
from uuid import UUID

import botocore
import boto3
import six

from magnetsdk2 import Connection, __version__
from magnetsdk2.cef import convert_alert
from magnetsdk2.iterator import FilePersistentAlertIterator
from magnetsdk2.time import UTC
from magnetsdk2.validation import parse_date

# logging setup
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
                                                 'Niddel Magnet v2 API (v{0:s})'.format(
                                                     __version__))
    parser.add_argument("-p", "--profile",
                        help="which profile (from ~/.magnetsdk/config) to obtain API key from",
                        default='default')
    parser.add_argument("-i", "--indent", help="indent JSON output", action="store_const", const=4)
    parser.add_argument("-v", "--verbose", help="set verbose mode", action="store_true",
                        default=False)
    parser.add_argument("-o", "--outfile",
                        help="destination file to write to, if exists will be overwritten",
                        type=argparse.FileType('wb'), default=stdout)
    parser.set_defaults(indent=None, parser=parser)
    subparsers = parser.add_subparsers()

    # "me" command
    me_parser = subparsers.add_parser('me', help="display API key owner information",
                                      description="display API key owner information")
    me_parser.set_defaults(func=command_me, parser=me_parser)

    # "organizations" command
    org_parser = subparsers.add_parser('organizations',
                                       help="list basic organization information",
                                       description="list basic organization information")
    org_parser.add_argument("--id", help="get details on organization with the provided ID",
                            type=UUID, required=False)
    org_parser.set_defaults(func=command_organizations, id=None, parser=org_parser)

    # "alerts" command
    alerts_parser = subparsers.add_parser('alerts',
                                          help="list an organization's alerts",
                                          description="list an organization's alerts")
    alerts_parser.add_argument("organization",
                               help="ID of the organization, if omitted the API key owner's " +
                                    "default organization is used",
                               nargs='?', type=UUID)
    alerts_parser.add_argument("--start", help="initial batch date to process in YYYY-MM-DD format",
                               type=parse_arg_date)
    alerts_parser.add_argument("-p", "--persist",
                               help="file to store persistent state data, to ensure only alerts " +
                                    "that haven't been seen before are part of the output")
    alerts_parser.add_argument("-f", "--format", choices=['json', 'cef'], default='json',
                               help="format in which to output alerts")
    alerts_parser.set_defaults(func=command_alerts, start=None, persist=None, parser=alerts_parser)

    # "whitelists" and "blacklists" commands
    for scope in ('white', 'black',):
        wlbl_parser = subparsers.add_parser(scope + 'lists',
                                            help="list an organization's " + scope + " list",
                                            description="list an organization's " + scope + " list")
        wlbl_parser.add_argument("organization",
                                 help="ID of the organization, if omitted the API key owner's " +
                                      "default organization is used",
                                 nargs='?', type=UUID)
        wlbl_parser.add_argument("--id", help="get details on " + scope + " list entry with the " +
                                              "provided ID",
                                 type=UUID, required=False)

        wlbl_parser.set_defaults(func=command_wl_bl, scope=scope)

    # "logs" command
    logs_parser = subparsers.add_parser('logs',
                                        help="upload, download or list log files",
                                        description="use temporary credentials to access " +
                                                    "log files to an organization's assigned " +
                                                    "S3 bucket's upload folder")
    logs_parser.add_argument("organization",
                             help="ID of the organization, if omitted the API key owner's " +
                                  "default organization is used",
                             type=UUID, nargs='?')
    logs_parser.set_defaults(parser=logs_parser)

    logs_subparsers = logs_parser.add_subparsers()

    # "logs list" command
    logs_list_parser = logs_subparsers.add_parser('list', help='list log files',
                                                  description='list files in the organization\'s ' +
                                                              'upload folder')
    logs_list_parser.add_argument("-f", "--format", choices=['json', 'table'], default='table',
                                  help="format in which to output alerts")

    logs_list_parser.set_defaults(func=command_logs_list, parser=logs_list_parser)

    # "logs upload" command
    logs_upload_parser = logs_subparsers.add_parser('upload', help='upload log files',
                                                    description='upload log files to the ' +
                                                                'organization\'s upload folder')
    logs_upload_parser.add_argument("-f", "--folder", default='',
                                    help="sub-folder of the upload folder to send file to")
    logs_upload_parser.add_argument("-p", "--prefix", choices=['day', 'hour'],
                                    required=False,
                                    help="prefix destination file name with UTC date in " +
                                         "YYYY-MM-DD format or hour in YYYY-MM-DD-HH format")
    logs_upload_parser.add_argument("src", help="source file name(s) or wildcard(s)", nargs="+")
    logs_upload_parser.set_defaults(func=command_logs_upload, parser=logs_upload_parser)

    # parse arguments
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # open connection and dispatch to proper function
    try:
        conn = Connection(profile=args.profile)
        args.func(conn, args)
    except Exception as e:
        logger.debug("exception caught in processing", exc_info=True)
        args.parser.error(e.message)
    else:
        if args.outfile != stdout:
            args.outfile.close()


def parse_arg_date(value):
    try:
        return parse_date(value)
    except Exception as e:
        logger.debug(e)
        raise argparse.ArgumentTypeError("unable to parse date, YYYY-MM-DD format expected")


def parse_glob_files(x):
    retval = set()
    if isinstance(x, six.string_types):
        retval |= set(glob(expanduser(x)))
    elif isinstance(x, list):
        for subx in x:
            retval |= parse_glob_files(subx)
    else:
        raise ValueError('unexpected type')
    return retval


def boto3_object_exists(obj):
    try:
        obj.load()
        return True
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            return False
        else:
            six.reraise(*exc_info())


def command_me(conn, args):
    json.dump(conn.get_me(), args.outfile, indent=args.indent)


def command_organizations(conn, args):
    if args.id:
        json.dump(conn.get_organization(args.id), args.outfile, indent=args.indent)
    else:
        for organization in conn.iter_organizations():
            try:
                json.dump(organization, args.outfile, indent=args.indent)
                args.outfile.write(linesep)
            except IOError as ioe:
                if ioe.errno == EPIPE and args.outfile == stdout:
                    logger.debug('stdout closed, exiting...')
                    break
                else:
                    six.reraise(*exc_info())


def command_alerts(conn, args):
    if not args.organization:
        args.organization = UUID(conn.get_me()['defaultOrganizationId'])
        logger.info('using default organization %s' % args.organization)

    if args.persist:
        iterator = FilePersistentAlertIterator(filename=args.persist, connection=conn,
                                               organization_id=args.organization,
                                               start_date=args.start)
    else:
        iterator = conn.iter_organization_alerts(organization_id=args.organization,
                                                 fromDate=args.start, sortBy='batchDate')

    if args.outfile != stdout and args.format == 'cef':
        args.outfile.write(BOM_UTF8)

    for alert in iterator:
        try:
            if args.format == 'json':
                json.dump(alert, args.outfile, indent=args.indent)
            elif args.format == 'cef':
                convert_alert(args.outfile, alert, args.organization)
            args.outfile.write(linesep)
        except IOError as ioe:
            if ioe.errno == EPIPE and args.outfile == stdout:
                logger.debug('stdout closed, exiting...')
                break
            else:
                six.reraise(*exc_info())

    if args.persist:
        iterator.save()


def command_logs_list(conn, args):
    if not args.organization:
        args.organization = UUID(conn.get_me()['defaultOrganizationId'])
        logger.info('using default organization %s' % args.organization)

    # connect to S3
    creds = conn.get_organization_credentials(args.organization)
    bucket = boto3.resource('s3', aws_access_key_id=creds['accessKeyId'],
                            aws_secret_access_key=creds['secretAccessKey'],
                            aws_session_token=creds['sessionToken'],
                            region_name=creds['bucketRegion']).Bucket(creds['bucket'])
    logger.debug('opened S3 bucket %s in %s successfully', creds['bucket'], creds['bucketRegion'])
    prefix = conn.get_organization(args.organization)['properties']['bucketUploadPrefix']

    # list objects
    for key in bucket.objects.filter(Prefix=prefix + '/'):
        name = 's3://{0:s}/{1:s}'.format(key.bucket_name, key.key)
        last_modified = key.last_modified.strftime('%c')
        try:
            if args.format == 'json':
                json.dump({'name': name, 'size': key.size, 'last_modified': last_modified},
                          args.outfile, indent=args.indent)
            elif args.format == 'table':
                args.outfile.write('{0:s} {1:-12d} {2:s}'.format(last_modified, key.size, name))
            args.outfile.write(linesep)
        except IOError as ioe:
            if ioe.errno == EPIPE and args.outfile == stdout:
                logger.debug('stdout closed, exiting...')
                break
            else:
                six.reraise(*exc_info())


def command_logs_upload(conn, args):
    if not args.organization:
        args.organization = UUID(conn.get_me()['defaultOrganizationId'])
        logger.info('using default organization %s' % args.organization)

    # get all source files and perform basic sanity checking
    srcfiles = parse_glob_files(args.src)
    if not srcfiles:
        raise Exception('no valid source files found')
    notfiles = {'"' + x + '"' for x in srcfiles if not isfile(x)}
    if notfiles:
        raise Exception('invalid files found: {0:s}'.format(', '.join(notfiles)))
    del notfiles

    # connect to S3
    creds = conn.get_organization_credentials(args.organization)
    bucket = boto3.resource('s3', aws_access_key_id=creds['accessKeyId'],
                            aws_secret_access_key=creds['secretAccessKey'],
                            aws_session_token=creds['sessionToken'],
                            region_name=creds['bucketRegion']).Bucket(creds['bucket'])
    logger.debug('opened S3 bucket %s in %s successfully', creds['bucket'], creds['bucketRegion'])

    # get remote file path
    uploadprefix = conn.get_organization(args.organization)['properties'][
        'bucketUploadPrefix']

    # determine filename prefix to use, if any
    if args.prefix == 'day':
        slotprefix = datetime.now(UTC).strftime("%Y-%m-%d_")
    elif args.prefix == 'hour':
        slotprefix = datetime.now(UTC).strftime("%Y-%m-%d-%H_")
    else:
        slotprefix = ''

    # process each file
    if sep != '/':
        uploadprefix = uploadprefix.replace('/', sep)
    for src in srcfiles:
        # assemble destination S3 key with full path
        dest = join(uploadprefix, args.folder, slotprefix + basename(src))
        if sep != '/':
            dest = dest.replace(sep, '/')

        # if key doesn't already exist, upload it
        try:
            args.outfile.write(
                'copying {0:s} to s3://{1:s}/{2:s} ...'.format(src, creds['bucket'], dest))
            obj = bucket.Object(dest)
            if boto3_object_exists(obj):
                args.outfile.write(' Remote file exists, skipping.')
            else:
                obj.upload_file(src, ExtraArgs={'ServerSideEncryption': 'AES256'})
                args.outfile.write(' Done.' + linesep)
            del obj
        except IOError as ioe:
            if ioe.errno == EPIPE and args.outfile == stdout:
                logger.debug('stdout closed, exiting...')
                break
            else:
                six.reraise(*exc_info())


def command_wl_bl(conn, args):
    if not args.organization:
        args.organization = UUID(conn.get_me()['defaultOrganizationId'])
        logger.info('using default organization %s' % args.organization)

    if args.id:
        json.dump(conn._get_organization_wblist_entry(args.scope, args.organization,
                                                      args.id), args.outfile, indent=args.indent)
    else:
        for alert in conn._list_organization_wblists(args.scope, args.organization):
            try:
                json.dump(alert, args.outfile, indent=args.indent)
                args.outfile.write(linesep)
            except IOError as ioe:
                if ioe.errno == EPIPE and args.outfile == stdout:
                    logger.debug('stdout closed, exiting...')
                    break
                else:
                    six.reraise(*exc_info())


if __name__ == "__main__":
    main()
