from .Datetime import Datetime
from .Parser import Parser

import logging
from logging import handlers

logging.basicConfig(level=logging.INFO, format='%(asctime)s [ %(levelname)s ] :: %(message)s', datefmt="%Y-%m-%dT%H:%M:%S", handlers=[
    handlers.RotatingFileHandler('debug.log'),  
    logging.StreamHandler()  
])