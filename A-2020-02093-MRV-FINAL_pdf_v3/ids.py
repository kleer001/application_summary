"""The DFO file-number shape, in one place because three modules match on it."""
import re

FILE_RX = re.compile(r"\d{2}-H[A-Z]{3}-\d{5}")
