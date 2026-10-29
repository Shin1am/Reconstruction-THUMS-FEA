"""Single place for the data root. Override with env var BIODAT_ROOT (folder that contains Data/)."""
import os

DATA_ROOT = os.environ.get('BIODAT_ROOT', r'G:/My Drive/BioDat_Yusuke_lab')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
