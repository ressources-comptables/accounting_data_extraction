"""
Module: main_handler_amount.py

Description:
This module contains various functions utilized for processing amounts present in text.

Functions:

process_amount():
    This is the main function for the initial processing of amounts present in the text. It determines whether there is an amount in the text and, if so, identifies the type of amount it is: composite amount or simple amount. 
    An "amount composite" refers to amounts that can contain different currencies and values, such as "VI fl. XII l. II s. vien. XXI l. gros." On the other hand, an "amount simple" is expressed only in one currency, such as "VI fl" or "XII l. II s. vien.". The "amount composite" consists of multiple "amount simple" elements. 
    Each line in the text can contain either composite amounts or simple amounts. If a composite amount is found, it is divided into simple amounts, and each simple amount is processed using the function process_amount_simple().

process_amount_simple():
    This function processes simple amounts.

process_subpart():
    Each simple amount can be divided into different parts. For example, the amount "XII l. II s. vien." can be divided into "XII l." and "II s.". Each part represents a subdivision of the amount (e.g., livre, sou, denier). 
    This function processes each of these subparts of the simple amount.

convert_roman_to_arabic_complex():
    This function converts complex composite numbers like "VM IIIC XII" into Arabic numerals. 
    To convert each part of this complex composite number, the function calls the more general function "convert_roman_to_arabic()" from date_handler.py.

"""

# Import libraries
# ------------------------------------------
import re # to work with regular expressions

# Import custom functions
# ------------------------------------------
from main_handler_date import convert_roman_to_arabic


# ============================
# Pre-process amount
# ============================

def process_amount(cursor, line, line_id):

    # Initialize variables
    amount_composite_uncertainty = 0
    amount_composite_extracted = None
    amount_simple_extracted = None

    # Extract part of text with possible amounts
    # (or after ":" or just start from first occurence of roman numerals)
    # ------------------------------------------------------------------

    # Using regular expression to find text after ":"
    match = re.search(r':\s*(.*)', line)

    # if found ":" got the part after this
    if match:
        extracted_part_with_amounts = match.group(1)

    # if not found ":" then search for first occurence of roman numerals
    else:
        match = re.search('[IVXLCDM]', line[1:])
        if match:
            extracted_part_with_amounts = line[match.start() + 1:]
        else:
            amount_composite_uncertainty = "1" # if not found amount, warning - need to check manually
            extracted_part_with_amounts = None
            return

    # Define amount type (composite or simple)
    # ------------------------------------------
            
    # extract amounts from the previously extracted text
    # This is a main regex to find all parts of amounts. See more detailed explanations in the manual
    amounts_extracted = re.findall(r'(?:minus\s)*[IVXLCDM]+(?:\s[IVXLCDM]+)*\s\b(?!l|d|s|o|p|m)(?!minus)[a-z]+\b\.*(?:\s\b(?!l|d|s|o|p|m)(?!minus)[a-z]+\b\.*)*|(?:minus\s)*(?:[IVXLCDM]+(?:\s[IVXLCDM]+)*\s(?:\b(?=l|d|s|o|p|m)(?!minus)[a-z]+\b)+\.*)+(?:\s[IVXLCDM]+\s(?:\b(?=l|d|s|o|p|m)(?!minus)[a-z]+\b)+\.*)*(?:\s(?!minus)[a-z]*\.*)*', extracted_part_with_amounts)

    # count amounts in the extracted text to know if it is composite or simple amount
    count_amounts = len(amounts_extracted)

    # if more than 10 parts in the extracted text, there is possible problem, need to check manually
    if count_amounts > 10 or count_amounts == 0:
        amount_composite_uncertainty = "1"
    
    # if more than 1 part, this is a composite amount
    elif count_amounts > 1:
        amount_composite_extracted = amounts_extracted
    
    # else, this is a simple amount
    else:
        amount_simple_extracted = amounts_extracted


    # Process amount composite
    # ------------------------------------------
    if amount_composite_extracted:

        # Insert into amount_composite table
        cursor.execute("INSERT INTO amount_composite (line_id, amount_composite_extracted, amount_composite_uncertainty) VALUES (%s, %s, %s)", (line_id, extracted_part_with_amounts, amount_composite_uncertainty,))

        # Retrieve auto-incremented ID
        amount_composite_id = cursor.lastrowid

        # Check if amount_composite_extracted contains the beginning of "singul" or "computa"
        check_exchange_rate = re.search(r'\b(singul|computa)\w*\b', extracted_part_with_amounts, re.IGNORECASE)

        if check_exchange_rate:
            # Retrieve date_id from line table
            # cursor.execute("SELECT date_id FROM line WHERE line_id = %s", (line_id,))
            # Retrieve auto-incremented ID
            # date_id = cursor.fetchone()[0]

            # OLD / Insert into exchange_rate table
            # cursor.execute("INSERT INTO exchange_rate (exchange_rate_extracted) VALUES (%s)", (extracted_part_with_amounts,))
            # exchange_rate_id = cursor.lastrowid

            # OLD / Insert into exchange_rate_internal_reference table
            # cursor.execute("INSERT INTO exchange_rate_internal_reference (line_id, exchange_rate_id) VALUES (%s, %s)", (line_id, exchange_rate_id,))

            # Check if the row with the same line_id already exists in the exchange_rate_internal_reference table
            cursor.execute("SELECT COUNT(*) FROM exchange_rate_internal_reference WHERE line_id = %s", (line_id,))
            count_existing = cursor.fetchone()[0]

            # If the line_id does not exist, insert the new data
            if count_existing == 0:
                # Insert into exchange_rate_internal_reference table
                cursor.execute("INSERT INTO exchange_rate_internal_reference (exchange_rate_extracted, line_id) VALUES (%s, %s)", (extracted_part_with_amounts, line_id,))



        # Process each part of amount_composite_extracted as amount_simple_extracted
        for amount_simple_extracted in amount_composite_extracted:
            line_id = None # there are no line_id case in this cas amount_simple will be linked directly to amount_composite
            process_amount_simple(cursor, line_id, amount_composite_id, amount_simple_extracted)


    # Process amount simple
    # ------------------------------------------
    elif amount_simple_extracted:
        amount_composite_id = None # there are no amount_composite_id case in this cas amount_simple will be linked directly to line
        # amount_simple_extracted = amount_simple_extracted[0]
        process_amount_simple(cursor, line_id, amount_composite_id, amount_simple_extracted[0])





# ============================
# Process amount simple
# ============================

# amount_simple_uncertainty = 1 : if more then 1 currency and if no sub-parts found

def process_amount_simple(cursor, line_id, amount_composite_id, amount_simple_extracted):

    # Initialize variables
    currency_extracted =  None
    currency_standardized_id = None
    arithmetic_operator = None
    amount_simple_uncertainty = 0

    # Convert amount_simple_extracted to a string if it's not already a string
    if not isinstance(amount_simple_extracted, str):
        amount_simple_extracted = str(amount_simple_extracted)

    # Process currencies
    # ------------------------------------------

    # extract currencies for simple amount
    currencies_extracted = re.findall(r'\b(?!l|d|s|o|p|m)(?!minus)[a-z]+\b\.*(?:\s[a-z]+\.*)*', amount_simple_extracted)

    # if there are many currencies, take the first one and report amount_simple_uncertainty
    if currencies_extracted:
        amount_simple_uncertainty = 1 if len(currencies_extracted) > 1 else None
        currency_extracted = currencies_extracted[0]

        """
        To identify currencies, we will take the first two letters of the extracted currency (two letters, because the smallest abbreviation is "fl") and look for standardized currencies that begin with these two letters. However, this method can produce errors. For this reason, for certain currencies whose names may be ambiguous and produce errors (most often currencies with two words in the name like "tur.parv" and "tur.gros"), we will clearly define the name to search for.
        """

        # Check if currency_extracted corresponds to (parv. tur.) ou (parve monete) ou (tur. parv.)"
        if re.search(r"\b(parv)", currency_extracted):
            currency_to_search = "turonensis parvorum"

        # Check if currency_extracted corresponds to (tur. gros.)
        elif re.search(r"\b(tur).*\b.*\b(gr).*\b", currency_extracted):
            currency_to_search = "grossus"

        # If none of the above conditions are met, take the first two characters of currency_extracted
        else:
            currency_to_search = currency_extracted[:2]


        # Search for currency_to_search in currency_name from the "currency_standardized" table
        cursor.execute("SELECT currency_standardized_id FROM currency_standardized WHERE currency_name LIKE %s", (f"{currency_to_search}%",))
        result_from_currency_standardized = cursor.fetchone()
       # cursor.fetchone() will take the only firs one result, to retrieve all possible results, use cursor.fetchall()

        if result_from_currency_standardized:
            currency_standardized_id = result_from_currency_standardized[0]  # Return the associated currency_standardized_id

        # If not found, search in currency_variant_name from the "currency_variant" table
        else: 
            cursor.execute("SELECT currency_standardized_id FROM currency_variant WHERE currency_variant_name LIKE %s", (f"{currency_to_search}%",))
        result_from_currency_variant = cursor.fetchone()
        if result_from_currency_variant:
            currency_standardized_id = result_from_currency_variant[0]
        # currency_standardized_id = cursor.fetchone()[0]


    # Process sub-parts of simple amount
    # ------------------------------------------
    # extract sub-parts from simple amount (e.g. "X" from "X fl. auri", or "IX s." and "VIII d." from "IX s. VIII d. tur. parvorum.")
    subparts_extracted = re.findall(r'[IVXLCDM]+(?:\s[IVXLCDM]+)*(?:\s\b(?=l|d|s|o|p|m)[a-z]+\b\.*)*', amount_simple_extracted)

    if not subparts_extracted:
        amount_simple_uncertainty = 1

    # Process arithmetic operator
    # ------------------------------------------
    # arithmetic_operator = re.search(r'\bminus\b', amount_simple_extracted)
    arithmetic_operator = 'minus' if re.search(r'\bminus\b', amount_simple_extracted) else None

    # Insert into table "amount_simple"
    # ------------------------------------------

    # Insert into amount_simple table
    cursor.execute("INSERT INTO amount_simple (line_id, amount_composite_id, amount_simple_extracted, currency_extracted, currency_standardized_id, arithmetic_operator, amount_simple_uncertainty) VALUES (%s, %s, %s, %s, %s, %s, %s)", (line_id, amount_composite_id, amount_simple_extracted, currency_extracted, currency_standardized_id, arithmetic_operator, amount_simple_uncertainty,))
    amount_simple_id = cursor.lastrowid


    # Call function to process sub-parts (need to call in the end, case need amount_simple_id)
    # ------------------------------------------
    if subparts_extracted:
        # process each sup-part
        for subpart_extracted in subparts_extracted:
            process_subpart(cursor, amount_simple_id, subpart_extracted)



# ============================
# Process subpart
# ============================

def process_subpart(cursor, amount_simple_id, subpart_extracted):

    # Inititalize variables
    amount_simple_subpart_uncertainty = 0
    roman_numeral = None

    # Process Roman numerals
    # ------------------------------------------
    roman_numerals = re.findall(r'[IVXLCDM]+(?:\s[IVXLCDM]+)*(?![a-z])', subpart_extracted)

    # if there are many Roman numerals, take the first one and report amount_simple_subpart_uncertainty
    if roman_numerals:
        amount_simple_subpart_uncertainty = 1 if len(roman_numerals) > 1 else None
        roman_numeral = roman_numerals[0]



    # Process Arabic numerals
    # ------------------------------------------

    arabic_numeral, amount_simple_subpart_uncertainty = convert_roman_to_arabic_complex(roman_numeral)


    # Process unit of count
    # ------------------------------------------

    unit_of_count_first_letter = re.search(r'\b(?=l|d|s|o|p|m)[a-z]', subpart_extracted) # this regex extract only first letter of unit of count
    # unit_of_count = re.findall(r'\b(?=l|d|s|o)[a-z]+\b\.*', subpart_extracted) # regex to extract all unit of count

    # dictionnary for first lettre of unit of count
    unit_of_count_prefix_to_id = {
        'l': '1',
        's': '2',
        'd': '3',
        'o': '4',
        'p': '5',
        'm': '6'
    }

    if unit_of_count_first_letter:
        prefix = unit_of_count_first_letter[0]
        unit_of_count_id =  unit_of_count_prefix_to_id.get(prefix)
    else:
        unit_of_count_id = None # Set a default value for unit_of_count_id

    # Insert into table "amount_simple_subpart"
    # ------------------------------------------
    cursor.execute("INSERT INTO amount_simple_subpart (amount_simple_id, subpart_extracted, roman_numeral, arabic_numeral, amount_simple_subpart_uncertainty, unit_of_count_id) VALUES (%s, %s, %s, %s, %s, %s)", (amount_simple_id, subpart_extracted, roman_numeral, arabic_numeral, amount_simple_subpart_uncertainty, unit_of_count_id,))



# ==================================================
# Convert complex Roman numerals to Arabic numerals
# =================================================

# to convert complex composite numbers like "VM IIIC XII", etc.
def convert_roman_to_arabic_complex(roman_numeral_complex):

    # Check if the variable is a string
    if isinstance(roman_numeral_complex, str):
        roman_numeral_complex = roman_numeral_complex

    else:
        # If not, convert it to string and take the first element
        if roman_numeral_complex is not None:
            roman_numeral_complex = str(roman_numeral_complex)
        # If empty input
        else:
            number_converted = None
            uncertainty_conversion = 1
            return number_converted, uncertainty_conversion


    # Initialize variables
    uncertainty_conversion = None

    # split complex number into parts
    number_original_divided = re.findall(r'[IVXLCDM]+', roman_numeral_complex) 
    number_converted = 0
    # uncertainty_conversion = 0 # to report any errors

    # calculate the number of parts in amounts
    number_of_parts_in_amount = len(number_original_divided) 

    # usualy the full complex amount can consiste of 3 parts: thousand (...M), hundred (...C) and ten (I..XCIX)
    # so if there no parts or too many parts, we will report uncertainty but process each part
    if number_of_parts_in_amount > 3 or number_of_parts_in_amount == 0: 
        uncertainty_conversion = 1
    
    # process each part of complex number
    for number_part in number_original_divided: 
        length = len(number_part) # check the the length of value (to hundle numbers like just "M" or just "C")
        last_char = number_part[-1] # assign variable to last character of number (to identifiy the parts of "thousand" or "hundred)

        if length > 1:  # if the length is greater than 1 (it means that it is not a just "M" or just "C")
            if last_char == 'M' and number_part != 'CM': # construct the part of "thousand"
                number_part_list = [number_part[:-1]] # convert string to list to be able to use function "convert_roman_to_arabic"
                converted_part, uncertainty_conversion = convert_roman_to_arabic(number_part_list)
                # the result of function convert_roman_to_arabic is a list, to make a calulation we need to take a only first element (there is anyway only one element in list) and convert it to integer (same for all others below)
                number_converted += int(converted_part[0]) * 1000
            elif last_char == 'C' and number_part != 'XC': # construct the part of "hundred"
                number_part_list = [number_part[:-1]] # convert string to list to be able to use function "convert_roman_to_arabic"
                converted_part, uncertainty_conversion = convert_roman_to_arabic(number_part_list)
                number_converted += int(converted_part[0]) * 100
            else: # if not part of "thousand" or "hundred",then it is "simple" number
                number_part_list = [number_part] # convert string to list to be able to use function "convert_roman_to_arabic"
                converted_part, uncertainty_conversion = convert_roman_to_arabic(number_part_list)
                number_converted += int(converted_part[0])
        else: # if the length is less than 1 (it means that it is or a just "M" or just "C" or just a simple number like "XII", etc.)
            number_part_list = [number_part] # convert string to list to be able to use function "convert_roman_to_arabic"
            converted_part, uncertainty_conversion = convert_roman_to_arabic(number_part_list)
            number_converted += int(converted_part[0])
    return number_converted, uncertainty_conversion # return full converted number (it may also complex as simple number)

