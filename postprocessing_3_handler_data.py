"""
Module: postprocessing_handler_data.py

Description:
This file contains general functions for postprocess all data step by step. Each function is called as a step from the file postprocessing_main.py. For more details, see README.md

Functions:
1. process_amount_simple_from_exchange_rate(cursor): 
    Process simple amounts entered for exchange rates.

2. conversion_amounts_to_smallest_unit_of_count(cursor):
    Convert all amounts to the smallest units of account.

3. calculate_exchange_rate_value(cursor):
    Calculate the values of exchange rates.

4. convert_amounts_simple_to_common_currency(cursor, currency_to_convert_to):
    Convert simple amounts to a common currency.

5. convert_amounts_compositie_to_common_currency(cursor, currency_to_convert_to):
    Convert composite amounts to a common currency.

Function "process_person_name_and_role" is DEPRICATED in this file. 
To faciliated manual treatement, this function was moved as separated postprocessing, see: postprocessing_2_person_name_and_role.py
6. process_person_name_and_role(cursor):
    Standardize person names and extract their roles.

"""

# Import libraries
# ------------------------------------------
import re # to work with regular expressions


# Import custom functions
# ------------------------------------------
from main_handler_amount import process_subpart
from postprocessing_3_handler_exchange_rate import find_exchange_rate_value, cross_currency_triangulation

# =====================================================================
# Step 4.1 Processing simple amounts entered for exchange rates
# =====================================================================

def process_amount_simple_from_exchange_rate(cursor):

    cursor.execute("""
        SELECT DISTINCT asimple.amount_simple_id, asimple.amount_simple_extracted 
        FROM amount_simple asimple 
        LEFT JOIN amount_simple_subpart ass 
        ON asimple.amount_simple_id = ass.amount_simple_id 
        WHERE asimple.amount_composite_id IS NULL 
        AND asimple.line_id IS NULL 
        AND ass.amount_simple_subpart_id IS NULL
    """)

    # Fetch the results
    results = cursor.fetchall()

    # Iterate over the results
    for row in results:
        amount_simple_id = row[0]
        amount_simple_extracted = row[1]

        # extract sub-parts from simple amount (e.g. "X" from "X fl. auri", or "IX s." and "VIII d." from "IX s. VIII d. tur. parvorum.")
        subparts_extracted = re.findall(r'[IVXLCDM]+(?:\s[IVXLCDM]+)*(?:\s\b(?=l|d|s|o|p|m)[a-z]+\b\.*)*', amount_simple_extracted)

        if subparts_extracted:
            # process each sup-part
            for subpart_extracted in subparts_extracted:
                process_subpart(cursor, amount_simple_id, subpart_extracted)

    print("Simple amounts manually entered for exchange rates have been processed.")



# =====================================================================
# Step 4.2 Conversion of all amounts to the smallest units of account
# =====================================================================

def conversion_amounts_to_smallest_unit_of_count(cursor):

    # Retrieve  amount_simple_id wich is not alread processed (amount_converted_to_smallest_unit_of_count IS NULL) and wich have units of counts (unit_of_count_id IS NOT NULL)
    cursor.execute("""
    SELECT
        DISTINCT ass.amount_simple_id
    FROM
        amount_simple_subpart ass
    INNER JOIN amount_simple asimple ON
        ass.amount_simple_id = asimple.amount_simple_id
    WHERE
        asimple.amount_converted_to_smallest_unit_of_count IS NULL
        AND ass.unit_of_count_id IS NOT NULL""")

    amount_simple_ids = cursor.fetchall()


    # Process each amount_simple_id
    for amount_simple_id_tuple in amount_simple_ids:
        amount_simple_id = amount_simple_id_tuple[0]  # type: ignore # Extract the value from the tuple

        # Retrieve relevant data from amount_simple_subpart
        cursor.execute("SELECT arabic_numeral, unit_of_count_id FROM amount_simple_subpart WHERE amount_simple_id = %s AND unit_of_count_id IS NOT NULL", (amount_simple_id,)) # type: ignore
        data = cursor.fetchall()

        # Initialize variables for calculations
        denarius_from_libre = 0
        denarius_from_solidus = 0
        denarius = 0
        denarius_from_obolus = 0
        denarius_from_picta = 0
        denarius_from_maille = 0
        smallest_unit_of_count_uncertainty = None

        # Perform calculations based on unit_of_count_id
        """
        Here are the different units of currencies that were used:

        libra / libris // [livre] // lb.
        solidus / solidi // [sou] // s.
        denarius / denarii // [denier] // d.
        obolus / oboli // [obole] // ob.
        picta // [picte] // pict.

        And here is their equivalence system:
        
        1 libra = 240 denarii
        1 solidus = 12 denarii
        1 denarius = 1 denarius
        1 obolus = 0.5 denarius
        1 picta = 0.25 denarius
        1 maille = 0.5 denarius
        """
        for arabic_numeral, unit_of_count_id in data:
            arabic_numeral = int(arabic_numeral)  # type: ignore # Convert to integer if it's supposed to be an integer
            if unit_of_count_id == 1:
                denarius_from_libre += arabic_numeral * 240
            elif unit_of_count_id == 2:
                denarius_from_solidus += arabic_numeral * 12
            elif unit_of_count_id == 3:
                denarius += arabic_numeral
            elif unit_of_count_id == 4:
                denarius_from_obolus += arabic_numeral * 0.5
            elif unit_of_count_id == 5:
                denarius_from_picta += arabic_numeral * 0.25
            elif unit_of_count_id == 6:
                denarius_from_maille += arabic_numeral * 0.5
            else:
                smallest_unit_of_count_uncertainty = 1

        # Calculate amount_converted_to_smallest_unit_of_count
        amount_converted_to_smallest_unit_of_count = denarius_from_libre + denarius_from_solidus + denarius + denarius_from_obolus + denarius_from_picta + denarius_from_maille

        if amount_converted_to_smallest_unit_of_count != 0:
            # Update the corresponding row in the amount_simple table
            cursor.execute("UPDATE amount_simple SET smallest_unit_of_count_uncertainty = %s, amount_converted_to_smallest_unit_of_count = %s WHERE amount_simple_id = %s", (smallest_unit_of_count_uncertainty, amount_converted_to_smallest_unit_of_count, amount_simple_id)) # type: ignore

    # Commit the transaction
    # cursor.connection.commit()

    print("The amounts have been converted to the smallest units of count.")


# =====================================================================
# Step 4.2.1 Process amounts without units of account
# =====================================================================

"""
The goal is to have in the same table "amount_simple" all the amounts combined: 
 - for the amounts which have accounting units these are then the amounts converted into the smallest unit;
 - for the amounts without accounting units for the original amounts (expressed in Arabic numerals).
Of course, we can fetch the amounts without accounting units in the "amount_simple_subpart" table, but it is not very practical to do it every time and it is preferable to have all the amounts that we will need to make calculations expressed in Arabic numerals in the same place.
"""

def process_amounts_without_unit_of_count(cursor):

    # Retrieve  amount_simple_id wich is not alread processed (amount_converted_to_smallest_unit_of_count IS NULL) and wich have units of counts (unit_of_count_id IS NOT NULL)
    cursor.execute("""
    SELECT
        DISTINCT ass.amount_simple_id
    FROM
        amount_simple_subpart ass
    INNER JOIN amount_simple asimple ON
        ass.amount_simple_id = asimple.amount_simple_id
    WHERE
        asimple.amount_without_unit_of_count IS NULL
        AND ass.unit_of_count_id IS NULL""")

    amount_simple_ids = cursor.fetchall()


    # Process each amount_simple_id
    for amount_simple_id_tuple in amount_simple_ids:
        amount_simple_id = amount_simple_id_tuple[0]  # type: ignore # Extract the value from the tuple

        # Retrieve relevant data from amount_simple_subpart
        cursor.execute("SELECT arabic_numeral FROM amount_simple_subpart WHERE amount_simple_id = %s AND unit_of_count_id IS NULL", (amount_simple_id,)) # type: ignore
        # data = cursor.fetchall()
        amount_without_unit_of_count = cursor.fetchone()[0]

        if amount_without_unit_of_count:
            # Update the corresponding row in the amount_simple table
            cursor.execute("UPDATE amount_simple SET amount_without_unit_of_count = %s WHERE amount_simple_id = %s", (amount_without_unit_of_count, amount_simple_id)) # type: ignore

    # Commit the transaction
    # cursor.connection.commit()

    print("The amounts without units of count have been processed.")

# =================================================
# Step 4.3 Calculation of values of exchange rates
# =================================================

def calculate_exchange_rate_value(cursor):
    # We select all exchange rates which have target and source currency
    # and where exchange_rate_value is NULL
    cursor.execute("""
    SELECT
        er.exchange_rate_id,
        CASE
            WHEN source.amount_simple_id IS NULL THEN 1
            ELSE source.amount_converted_to_smallest_unit_of_count
        END AS amount_base,
        CASE
            WHEN target.amount_simple_id IS NULL THEN 1
            ELSE
                CASE
                    WHEN target.amount_converted_to_smallest_unit_of_count IS NOT NULL THEN target.amount_converted_to_smallest_unit_of_count
                    WHEN target.amount_converted_to_smallest_unit_of_count IS NULL AND target.amount_without_unit_of_count IS NOT NULL THEN target.amount_without_unit_of_count
                    ELSE 1
                END
        END AS amount_quote
    FROM
        exchange_rate er
    LEFT JOIN 
        amount_simple source ON
        er.amount_simple_source_id = source.amount_simple_id
    LEFT JOIN 
        amount_simple target ON
        er.amount_simple_target_id = target.amount_simple_id
    WHERE
        er.currency_source_id IS NOT NULL
        AND 
        er.currency_target_id IS NOT NULL
        AND
        er.exchange_rate_value IS NULL
    """)

    # Fetch the results
    results = cursor.fetchall()

    processed_count = 0  # Track the number of processed exchange rates

    # Iterate over the results
    for row in results:
        exchange_rate_id = row[0]
        amount_base = row[1]
        amount_quote = row[2]

        # Ensure both amounts are not None before calculation and avoid division by zero
        if amount_base is not None and amount_quote is not None and amount_base != 0:
            # calculate the value of exchange rate
            exchange_rate_value = amount_quote / amount_base

            # Insert the exchange_rate_value in the exchange_rate table
            cursor.execute("UPDATE exchange_rate SET exchange_rate_value = %s WHERE exchange_rate_id = %s", (exchange_rate_value, exchange_rate_id))
            processed_count += 1

    # Commit the transaction
    # cursor.connection.commit()

    print(f"{processed_count} exchange rates have been processed and updated.")


# ==========================================
# Step 4.4 Conversion to a common currency
# ==========================================

"""
When converting amounts to a common currency, there are two steps:
 - 1) During the first step, all single amounts are converted. 
 - 2) During the second step, all single amounts that make up a composite amount will be added together. However, it should be noted that certain single amounts that are part of composite amounts must be subtracted from the final amount (these amounts are marked in the database with the column "arithmetic operation" containing the value "minus").
"""


# =============================================================
# Step 4.4.1 Conversion of amounts simple to a common currency
# =============================================================

def convert_amounts_simple_to_common_currency(cursor, currency_to_convert_to):

    # Define the currency to which we convert
    # currency_to_convert_to = "1"
    exchange_rate_id = None
    exchange_rate_id_additional = None
    amount_original = None


    # Find all amounts to convert
    # --------------------------------------------------------------

    """
    This query allows extracting all values representing the amounts to be converted. For simple amounts that can be broken down into units of account, this value equals the amount converted into the smallest unit of account (by default, it's denier). For simple amounts not divisible into units of account, this value equals the original amount (converted into Arabic numerals). This query returns the identifiers of the simple amounts, the names of currencies, and the values of the amounts to be converted. If the value of the amount to be converted could not be established (meaning simple amounts divisible into units of account have not yet been converted into the smallest units), it returns a "null" value. This allows having all the values and sorting them after the query if necessary.
    This query also returns the date (start_date_standardized) associated with the line from which the simple amount or composite amount was extracted. This date is necessary to correctly select the appropriate exchange rates.
    """
    cursor.execute("""
    SELECT
        a.amount_simple_id,
        a.currency_standardized_id,
        CASE
            WHEN a.amount_converted_to_smallest_unit_of_count IS NOT NULL THEN a.amount_converted_to_smallest_unit_of_count
            ELSE
                CASE
                WHEN sub.unit_of_count_id IS NULL THEN sub.arabic_numeral
                ELSE NULL
            END
        END AS amount_to_convert,
        CASE
            WHEN a.line_id IS NOT NULL THEN line_date.start_date_standardized
            ELSE composite_date.start_date_standardized
        END AS start_date_standardized
    FROM
        amount_simple a
    LEFT JOIN amount_simple_subpart sub ON
        a.amount_simple_id = sub.amount_simple_id
        AND sub.unit_of_count_id
    IS NULL
    LEFT JOIN line ON
        a.line_id = line.line_id
    LEFT JOIN DATE AS line_date ON
        line.date_id = line_date.date_id
    LEFT JOIN amount_composite AS composite ON
        a.amount_composite_id = composite.amount_composite_id
    LEFT JOIN line AS composite_line ON
        composite_line.line_id = composite.line_id
    LEFT JOIN DATE AS composite_date ON
        composite_line.date_id = composite_date.date_id
    """)

    # Fetch the list of amounts to convert
    amounts_to_convert_list = cursor.fetchall()

    # Iterate over the list of found amounts to convert
    for amount_to_convert_unit in amounts_to_convert_list:
        amount_simple_id = amount_to_convert_unit[0]
        currency_to_convert_from = amount_to_convert_unit[1] # This is the currency from which we convert !!!
        amount_to_convert = amount_to_convert_unit[2]
        amount_to_convert_date = amount_to_convert_unit[3]

        if amount_to_convert:

            # if the amount to convert is already in the currency to wich we want to convert we just copy this value in the table amount_converted and mark it as "original". The choice is made to keep all the amounts of the same currency (converted together with the originals) to then better manage the manipulation of this data in Python and in R (this avoids rebuilding all the amounts and their currencies each time for the add to converted amounts).
            if currency_to_convert_from == currency_to_convert_to:
                amount_converted = amount_to_convert
                amount_original = "1" # mark that it is a original (not converted) amount 

            # if the currency of amount_converted is not equal to currency of amount_to_convert then we make a conversion
            else:

                # Try to find the appropriate DIRECT exchange rate
                # (select by the currency to which we convert and by the closest date of exchange rate)
                # --------------------------------------------------------------------------------------
                exchange_rate_id, exchange_rate_value = find_exchange_rate_value(cursor, amount_to_convert_date, currency_to_convert_to, currency_to_convert_from)


                # if we found the DIRECT exchange rate
                if exchange_rate_value:
                    # Because it is the DIRECT exchange rate, we divide the amount by the exchange rate
                    amount_converted = amount_to_convert / exchange_rate_value

                else:
                    # Try to find the appropriate REVERSE exchange rate
                    """
                    If we dont have the exchange rate like this: 1 currency_to_convert_to = 100 currency_to_convert_from
                    But we have the exchange rate like this: 1 currency_to_convert_from = 100 currency_to_convert_to
                    We can also can use this exchange rate to conversion of amount, but the calculation will be different - instead of dividing by the exchange rate, we will multiply by.

                    If we dont find DIRECT exchange rate, we will search for REVERSE exchange rate. 
                    That means we change the order of currency_to_convert_from and the currency_to_convert_to.
                    Indeed, for exemple if we have the DIRECT exchange rate like this: 1 currency_to_convert_to = 100 currency_to_convert_from. 
                    """
                    exchange_rate_id, exchange_rate_value = find_exchange_rate_value(cursor, amount_to_convert_date, currency_to_convert_from, currency_to_convert_to)

                    # if we found the REVERSE exchange rate
                    if exchange_rate_value:
                        # Because it is the REVERSE exchange rate, we multiply the amount by the exchange rate
                        amount_converted = amount_to_convert * exchange_rate_value

                    # if no REVERSE exchange rate was found, then use cross-currency triangulation
                    else: 
                        amount_converted, exchange_rate_id, exchange_rate_id_additional = cross_currency_triangulation(cursor, amount_to_convert, amount_to_convert_date, currency_to_convert_to, currency_to_convert_from)



            if amount_converted:
                amount_converted = float("{:.3f}".format(amount_converted))
                # Insert or update the amount_converted table
                """
                if there are already a table with the same amount_simple_id and currency_standardized_id then update the values of exchange_rate_id and amount_converted
                """
                cursor.execute("""
                    INSERT INTO amount_converted (amount_simple_id, currency_standardized_id, exchange_rate_id, exchange_rate_id_additional, amount_converted, amount_original) 
                    VALUES (%s, %s, %s, %s, %s, %s) 
                    ON DUPLICATE KEY UPDATE 
                    exchange_rate_id = VALUES(exchange_rate_id), 
                    amount_converted = VALUES(amount_converted)
                """, (amount_simple_id, currency_to_convert_to, exchange_rate_id, exchange_rate_id_additional, amount_converted, amount_original))

                # If a new row was inserted, get the last insert id
                # amount_converted_id = cursor.lastrowid

                # Commit the transaction
                # cursor.connection.commit()

    print("All simple amounts was converted to common currency.")



# =================================================================
# Step 4.4.2 Conversion of amounts composites to a common currency
# =================================================================

def convert_amounts_compositie_to_common_currency(cursor, currency_to_convert_to):

    # Define the currency to which we convert
    # currency_to_convert_to = "1"

    cursor.execute("""
    SELECT
        asimple.amount_composite_id,
        asimple.amount_simple_id,
        asimple.arithmetic_operator,
        aconverted.amount_converted 
    FROM
        amount_simple asimple
        LEFT JOIN amount_converted aconverted ON asimple.amount_simple_id = aconverted.amount_simple_id 
    WHERE
        asimple.amount_composite_id IS NOT NULL
        AND aconverted.currency_standardized_id = %s
    """, (currency_to_convert_to,))

    # Fetching results from the cursor
    amounts_composite_list = cursor.fetchall()

    # Grouping amount_converted by amount_composite_id
    amounts_composite_group = {}
    for amount_composite_unit in amounts_composite_list:
        amount_composite_id = amount_composite_unit[0] # type: ignore
        amount_converted = amount_composite_unit[3] # type: ignore
        arithmetic_operator = amount_composite_unit[2] # type: ignore
        
        if amount_composite_id not in amounts_composite_group:
            amounts_composite_group[amount_composite_id] = []
            
        amounts_composite_group[amount_composite_id].append((amount_converted, arithmetic_operator))

    # New dictionary to store calculated values
    amounts_composite_converted = {}

    # Iterate over each amount_composite_id in amounts_composite_group
    for amount_composite_id, amount_converted_list in amounts_composite_group.items():
        # Initialize amount_composite_converted for current amount_composite_id
        amounts_composite_converted[amount_composite_id] = None
        
        # Iterate over each (amount_converted, arithmetic_operator) tuple for current amount_composite_id
        for amount_converted, arithmetic_operator in amount_converted_list:
            # If amount_converted is not None, update amount_composite_converted
            if amount_converted is not None:
                if amounts_composite_converted[amount_composite_id] is None:
                    amounts_composite_converted[amount_composite_id] = amount_converted
                else:
                    if not arithmetic_operator:
                        amounts_composite_converted[amount_composite_id] += amount_converted
                    elif arithmetic_operator == "minus":
                        amounts_composite_converted[amount_composite_id] -= amount_converted

    # Print or use the calculated amounts
    for amount_composite_id, amount_composite_converted_value in amounts_composite_converted.items():
        # print(f"Amount Composite ID: {amount_composite_id}, Amount Composite Converted: {amount_composite_converted_value}")

        cursor.execute("""
                        INSERT INTO amount_converted (amount_composite_id, currency_standardized_id, amount_converted) 
                        VALUES (%s, %s, %s) 
                        ON DUPLICATE KEY UPDATE 
                        amount_converted = VALUES(amount_converted)
                    """, (amount_composite_id, currency_to_convert_to, amount_composite_converted_value))

                    # If a new row was inserted, get the last insert id
                    # amount_converted_id = cursor.lastrowid

        # Commit the transaction
        # cursor.connection.commit()

    print("All composite amounts was converted to common currency.")


