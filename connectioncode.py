
import string
import math
import ipaddress

SYMBOLS = [str(i) for i in range(10)] + [*string.ascii_uppercase] # numbers 0-9 and English uppercase letters
BASE = len(SYMBOLS)
ENCODING_STRING_LENGTH = math.ceil(32 / math.log2(BASE))
CHECKSUM_CORRECT_SUM = 7

# connection code:
# - represents an ip address
# - the 32-bit integer is converted into base-<BASE>, represented with SYMBOLS
# - the sum all symbols (their indeces in SYMBOLS) mod <BASE> must be 0 (most incorrect codes can be detected with this)
# - the last letter in a connection string doesn't encode the ip, but makes the sum correct
# - case insensitive

def encode_ip_address(ip: str):
    number = int(ipaddress.IPv4Address(ip))
    encoding_string = number_to_encoding_symbol_string(number)
    checksum_symbol = get_correct_checksum_symbol(encoding_string)
    connection_code = encoding_string + checksum_symbol

    throw_if_invalid_connection_code(connection_code)
    return connection_code

def decode_connection_code(connection_code: str):
    connection_code = connection_code.upper() # because the code should be case insensitive
    throw_if_invalid_connection_code(connection_code)

    encoding_string = connection_code[:-1]
    number = encoding_symbol_string_to_number(encoding_string)
    return str(ipaddress.IPv4Address(number))

def number_to_encoding_symbol_string(num: int):
    symbol_string = ""
    while num > 0:
        i = num % BASE
        num //= BASE
        symbol_string += SYMBOLS[i]

    symbol_string = ''.join(reversed(symbol_string))# convert to major first
    symbol_string = symbol_string.rjust(ENCODING_STRING_LENGTH, SYMBOLS[0])# fix the length
    return symbol_string

def encoding_symbol_string_to_number(symbol_string: str):
    number = 0
    for i, symbol in enumerate(reversed(symbol_string)):
        number += SYMBOLS.index(symbol) * BASE**i

    return number

def get_sum_modulo(string: str):
    return sum([SYMBOLS.index(s) for s in string]) % BASE

def get_correct_checksum_symbol(symbol_string: str):
    uncorrected = get_sum_modulo(symbol_string)
    corrector = (CHECKSUM_CORRECT_SUM - uncorrected) % BASE# from equation (uncorrected + corrector) % BASE == CHECKSUM_CORRECT_SUM
    return SYMBOLS[corrector]

def throw_if_invalid_connection_code(connection_code: str):
    connection_code = connection_code.upper() # because the code should be case insensitive

    # assert valid characters
    for char in connection_code:
        assert char in SYMBOLS, f"Unexpected symbol '{char}'."

    # assert correct length
    correct_length = ENCODING_STRING_LENGTH + 1
    wrong_length_message = f"Wrong length. {len(connection_code)} instead of {correct_length} characters."
    assert len(connection_code) == correct_length, wrong_length_message

    # assert correct sum
    actual_sum = get_sum_modulo(connection_code)
    assert actual_sum == CHECKSUM_CORRECT_SUM, "Invalid code. Checksum failed."
