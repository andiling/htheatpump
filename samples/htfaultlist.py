#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#  htheatpump - Serial communication module for Heliotherm heat pumps
#  Copyright (C) 2019  Daniel Strigl

#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Command line tool to query for the fault list of the heat pump.

    Example:

    .. code-block:: shell

       $ python3 htfaultlist.py --device /dev/ttyUSB1 --baudrate 9600
       #000 [2000-01-01T00:00:00]: 65534, Keine Stoerung
       #001 [2000-01-01T00:00:00]: 65286, Info: Programmupdate 1
       #002 [2000-01-01T00:00:00]: 65285, Info: Initialisiert
       #003 [2000-01-01T00:00:16]: 00009, HD Schalter
       #004 [2000-01-01T00:00:20]: 00021, EQ Motorschutz
       #005 [2014-08-06T13:25:54]: 65289, Info: Manueller Init
       #006 [2014-08-06T13:26:10]: 65534, Keine Stoerung
       #007 [2014-08-06T13:26:10]: 65287, Info: Programmupdate 2
       #008 [2014-08-06T13:26:10]: 65285, Info: Initialisiert
       #009 [2014-08-06T13:26:37]: 65298, Info: L.I.D. geaendert
       #010 [2014-08-06T13:28:23]: 65534, Keine Stoerung
       #011 [2014-08-06T13:28:27]: 65534, Keine Stoerung
"""

import sys
import argparse
import textwrap
import json
import csv
from htheatpump.htheatpump import HtHeatpump
from timeit import default_timer as timer
import logging
_logger = logging.getLogger(__name__)


# Main program
def main():
    parser = argparse.ArgumentParser(
        description = textwrap.dedent('''\
            Command line tool to query for the fault list of the heat pump.

            Example:

              $ python3 %(prog)s --device /dev/ttyUSB1
              #000 [2000-01-01T00:00:00]: 65534, Keine Stoerung
              #001 [2000-01-01T00:00:00]: 65286, Info: Programmupdate 1
              #002 [2000-01-01T00:00:00]: 65285, Info: Initialisiert
              #003 [2000-01-01T00:00:16]: 00009, HD Schalter
              #004 [2000-01-01T00:00:20]: 00021, EQ Motorschutz
            '''),
        formatter_class = argparse.RawDescriptionHelpFormatter,
        epilog = textwrap.dedent('''\
            DISCLAIMER
            ----------

              Please note that any incorrect or careless usage of this program as well as
              errors in the implementation can damage your heat pump!

              Therefore, the author does not provide any guarantee or warranty concerning
              to correctness, functionality or performance and does not accept any liability
              for damage caused by this program or mentioned information.

              Thus, use it on your own risk!
            ''') + "\r\n")

    parser.add_argument(
        "-d", "--device",
        default = "/dev/ttyUSB0",
        type = str,
        help = "the serial device on which the heat pump is connected, default: %(default)s")

    parser.add_argument(
        "-b", "--baudrate",
        default = 115200,
        type = int,
        # the supported baudrates of the Heliotherm heat pump (HP08S10W-WEB):
        choices = [9600, 19200, 38400, 57600, 115200],
        help = "baudrate of the serial connection (same as configured on the heat pump), default: %(default)s")

    parser.add_argument(
        "-t", "--time",
        action = "store_true",
        help = "measure the execution time")

    parser.add_argument(
        "-v", "--verbose",
        action = "store_true",
        help = "increase output verbosity by activating logging")

    parser.add_argument(
        "-l", "--last",
        action = "store_true",
        help = "print only the last fault message of the heat pump")

    parser.add_argument(
        "-j", "--json",
        type = str,
        help = "write the fault list to the specified JSON file")

    parser.add_argument(
        "-c", "--csv",
        type = str,
        help = "write the fault list to the specified CSV file")

    args = parser.parse_args()

    # activate logging with level DEBUG in verbose mode
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    hp = HtHeatpump(args.device, baudrate=args.baudrate)
    start = timer()
    try:
        hp.open_connection()
        hp.login()

        rid = hp.get_serial_number()
        if args.verbose:
            _logger.info("connected successfully to heat pump with serial number {:d}".format(rid))
        ver = hp.get_version()
        if args.verbose:
            _logger.info("software version = {} ({:d})".format(ver[0], ver[1]))

        if args.last:
            # query for the last fault message of the heat pump
            idx, err, dt, msg = hp.get_last_fault()
            fault_lst = [{"index"   : idx,             # fault list index
                          "error"   : err,             # error code
                          "datetime": dt.isoformat(),  # date and time of the entry
                          "message" : msg,             # error message
                          }]
            print("#{:03d} [{}]: {:05d}, {}".format(idx, dt.isoformat(), err, msg))
        else:
            # query for the whole fault list of the heat pump
            fault_lst = []
            for e in hp.get_fault_list():
                e.update({"datetime": e["datetime"].isoformat()})  # convert datetime dict entry to str
                fault_lst.append(e)
                print("#{:03d} [{}]: {:05d}, {}".format(e["index"], e["datetime"], e["error"], e["message"]))

        if args.json:  # write fault list entries to JSON file
            with open(args.json, 'w') as jsonfile:
                json.dump(fault_lst, jsonfile, indent=4, sort_keys=True)

        if args.csv:  # write fault list entries to CSV file
            with open(args.csv, 'w') as csvfile:
                fieldnames = ["index", "datetime", "error", "message"]
                writer = csv.DictWriter(csvfile, delimiter='\t', fieldnames=fieldnames)
                writer.writeheader()
                for e in fault_lst:
                    writer.writerow({"index"   : e["index"],
                                     "datetime": e["datetime"],
                                     "error"   : e["error"],
                                     "message" : e["message"]
                                     })
    except Exception as ex:
        _logger.error(ex)
        sys.exit(1)
    finally:
        hp.logout()  # try to logout for an ordinary cancellation (if possible)
        hp.close_connection()
    end = timer()

    # print execution time only if desired
    if args.time:
        print("execution time: {:.2f} sec".format(end - start))

    sys.exit(0)


if __name__ == "__main__":
    main()
