# -*- coding: utf-8 -*-
"""
Created on Fri Sep  5 12:26:40 2014

:module-author: steffen
:filename: config.py


This module provides a high level layer for reading and writing config files.
There must be a file called "config.ini" in the root-folder of the project.
The file has to be of the following structure to be imported correctly.

# this is a comment \n
# the file structure is like: \n
 \n
[netCDF] \n
RootFolder = c://netCDF \n
FilePrefix = cd2_ \n
 \n
[mySQL] \n
host = localhost \n
user = guest \n
password = root \n
database = znes \n
 \n
[SectionName] \n
OptionName = value \n
Option2 = value2 \n


"""
import os
import logging
import configparser as cp


FILENAME = 'config.ini'
FILE = os.path.join(os.path.expanduser("~"), '.oemof', FILENAME)

cfg = cp.RawConfigParser()
_loaded = False


def load_config(filename=None):
    """
    Load data from config file to `cfg` that can be accessed by get, set
    afterwards.

    Specify absolute or relative path to your config file.

    :param filename: Relative or absolute path
    :type filename: str or list
    """
    # load config

    global FILE

    if filename is not None:
        FILE = filename
    init(FILE)


def main():
    pass


def init(file):
    """
    Read config file

    Parameters
    ----------
    file : str or list
        Absolute path to config file (incl. filename)
    """
    cfg.read(file)
    global _loaded
    _loaded = True


def get(section, key):
    """
    returns the value of a given key of a given section of the main
    config file.

    :param section: the section.
    :type section: str.
    :param key: the key.
    :type key: str.

    :returns: the value which will be casted to float, int or boolean.
    if no cast is successful, the raw string will be returned.

    """
    # FILE = 'config_misc'

    if not _loaded:
        init(FILE)
    try:
        return cfg.getint(section, key)
    except ValueError:
        try:
            return cfg.getfloat(section, key)
        except ValueError:
            try:
                return cfg.getboolean(section, key)
            except ValueError:
                try:
                    value = cfg.get(section, key)
                    if value == 'None':
                        value = None
                    return value
                except ValueError:
                    logging.error(
                        "section {0} with key {1} not found in {2}".format(
                            section, key, FILE))
                    return cfg.get(section, key)

if __name__ == "__main__":
    main()
