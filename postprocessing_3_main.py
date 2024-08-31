"""
Module: postprocessing_main.py

Description:
This is a main file for postprocessing data. For more detail see README.md
"""

# Import libraries
# ------------------------------------------


# Import custom functions
# ------------------------------------------
from database_config import connect_to_database
from postprocessing_3_handler_data import process_amount_simple_from_exchange_rate, conversion_amounts_to_smallest_unit_of_count, process_amounts_without_unit_of_count, calculate_exchange_rate_value, convert_amounts_simple_to_common_currency, convert_amounts_compositie_to_common_currency
#, process_person_name_and_role


# ==============================
# Functions
# ==============================


# Main function to process data
# ------------------------------------------
def postprocessing_main():

    # Establish connection cursor
    cursor = connection.cursor(buffered=True)

    # Define variables
    # -------------------------
    currency_to_convert_to = 6 # id of common currency to wich we want to convert
    # IMPORTANT!!! It is integer, not a string!!! Write it like this 6 (AND NOT "6")!!!! Otherwise it doesnt work!!!



    # Steps of post-processing
    # -------------------------

    # Step 4.1 Processing simple amounts entered for exchange rates
    process_amount_simple_from_exchange_rate(cursor)
    
    # Step 4.2 Conversion of all amounts to the smallest units of account
    conversion_amounts_to_smallest_unit_of_count(cursor)

    # Step 4.2.1 Process amounts without units of account
    process_amounts_without_unit_of_count(cursor)

    # Step 4.3 Calculation of values of exchange rates
    calculate_exchange_rate_value(cursor)

    # (The conversion functions can be used separatly each time we want to convert to different common currency)
    # Step 4.4 Conversion to a common currency
    # Step 4.4.1 Conversion of amounts simple to a common currency
    convert_amounts_simple_to_common_currency(cursor, currency_to_convert_to)
    # Step 4.4.2 Conversion of amounts composites to a common currency
    convert_amounts_compositie_to_common_currency(cursor, currency_to_convert_to)

    # Step 4.5 “Standardization” of person names and extraction of their roles
    # process_person_name_and_role(cursor)

    # Commit the transaction and close database connection
    connection.commit()
    cursor.close()
    connection.close()

    # Inform about the result
    print ("Data post-processing has been completed.")

# ==============================
# Processing
# ==============================

# connect to database
# -------------------------
connection = connect_to_database()

# process function main()
# -------------------------
if __name__ == "__main__":
    postprocessing_main()