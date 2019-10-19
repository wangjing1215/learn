import logging
import os

# create logger
logger = logging.getLogger('klz')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "runtime/log.txt")
if not os.path.exists(log_file):
    f = open(log_file, 'w')
    f.close()
ch = logging.FileHandler(log_file)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(pathname)s -%(lineno)d- %(funcName)s %(message)s')
# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)
