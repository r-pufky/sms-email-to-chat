#!/usr/bin/python
#
# Command line wrapper for sms_to_chat.
#

import logging
import optparse
import sys

import sms_to_chat


def ParseArgs(args):
  """ Process command line arguements.

  Args:
    args: sys.argv options.

  Returns:
    Dictionary containing arguements to use.
  """
  parser = optparse.OptionParser()
  parser.add_option('-m', '--maildir', action='store', type='string',
      dest='maildir',
      help='Maildir directory to process.')
  parser.add_option('-e', '--export', action='store', type='string',
      dest='export',
      help='Directory to export chat logs to.')
  parser.add_option('-t', '--timezone', action='store', type='string',
      dest='timezone', default='America/Los_Angeles',
      help='Timezone to assume SMS messages were recieved. '
           'Default: America/Log_Angeles')
  parser.add_option('-l', '--log', action='store', type='string',
      dest='log', default='WARNING',
      help='Logging level to use (DEBUG, INFO, WARNING, ERROR, CRITICAL) '
           'Default: WARNING')
  return parser.parse_args(args)[0]


def main(args):
  options = ParseArgs(args)
  logging.basicConfig(level=getattr(logging, options.log.upper(), None))
  sms_chat = sms_to_chat.SmsToChat(options.maildir, options.timezone)
  sms_chat.Process()


if __name__ == '__main__':
  main(sys.argv)  
