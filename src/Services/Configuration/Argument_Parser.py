from RuntimeContants import Runtime_Datasets
import argparse
from Services.Configuration.Config import Config
from time import sleep


def handle_args():
    """
    Parse the given arguments
    :return:
    """

    parser = argparse.ArgumentParser(description='Get the impact of tool features on it\'s runtime.',
                                     epilog='Accepts tsv and csv files')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', required=False,
                        help="Enables the verbose mode. With active verbose mode additional information"
                             "is shown in the console")
    parser.add_argument('-mg', '--merge', dest='merge', required=False, action='store_true',
                        help="Merges all available versions of a tool together.")
    parser.add_argument('-r', '--remove', dest='remove', action='store_true', required=False,
                        help="Activates the removal of data for further evaluation of data sets")
    parser.add_argument('-m', '--memory', dest='memory', action='store_true', required=False,
                        help="If set, the application will run in memory saving mode."
                             "Should only be used where memory is limited.")
    parser.add_argument('-d', '--debug', dest='debug', action='store_true', required=False,
                        help="If set, the tool will run in debug mode. You will get developer output. The performance"
                             "is most likely be not as fast as possible!")
    args = parser.parse_args()

    if args.remove:
        Config.PERCENTAGE_REMOVAL = True

    if args.verbose:
        Config.VERBOSE = True

    if args.merge:
        Config.MERGED_TOOL_EVALUATION = True

    if args.memory:
        Config.MEMORY_SAVING_MODE = True

    if args.debug:
        Config.VERBOSE = True
        Config.DEBUG_MODE = True

    sleep(1)
