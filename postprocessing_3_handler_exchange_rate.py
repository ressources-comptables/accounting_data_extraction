"""
Module: postprocessing_handler_exchange_rate.py

Description:
This module contains functions for handling exchange rates and currency conversions.

List of Functions:
1. find_exchange_rate_value(cursor, amount_to_convert_date, currency_to_convert_to, currency_to_convert_from):
    Find the appropriate exchange rate given currencies and a date.

2. cross_currency_triangulation(cursor, amount_to_convert, amount_to_convert_date, currency_to_convert_to, currency_to_convert_from):
    Perform cross-currency triangulation to convert an amount between two currencies.
"""

# Import libraries
# ------------------------------------------
import pandas # to manipulate data

# ==========================================
# Find the appropriate exchange rate
# ==========================================

def find_exchange_rate_value(cursor, amount_to_convert_date, currency_to_convert_to, currency_to_convert_from):

    # Define variables
    exchange_rate_id = None
    exchange_rate_value = None

    # Find the appropriate DIRECT exchange rate
    # (select by the currency to which we convert and by the closest date of exchange rate)
    # --------------------------------------------------------------
    cursor.execute("""
    SELECT 
        result.exchange_rate_id,
        result.currency_source_id,
        result.currency_target_id,
        result.exchange_rate_value,
        result.start_date_standardized
    FROM 
        (
            SELECT 
                line_date.start_date_standardized,
                exchange_rate.exchange_rate_id,
                exchange_rate.currency_source_id,
                exchange_rate.currency_target_id,
                exchange_rate.exchange_rate_value,
                ABS(DATEDIFF(line_date.start_date_standardized, %s)) AS date_difference
            FROM 
                line AS line_inner
            INNER JOIN exchange_rate_internal_reference ON line_inner.line_id = exchange_rate_internal_reference.line_id
            INNER JOIN exchange_rate ON exchange_rate_internal_reference.exchange_rate_id = exchange_rate.exchange_rate_id
            INNER JOIN date AS line_date ON line_inner.date_id = line_date.date_id
            WHERE
                exchange_rate.currency_source_id = %s
                AND exchange_rate.currency_target_id = %s
            ORDER BY 
                date_difference
            LIMIT 1
        ) AS result
    """, (amount_to_convert_date, currency_to_convert_to, currency_to_convert_from,)) # type: ignore

    # Fetch the results
    exchange_rate_found = cursor.fetchone()

    # if appropriate exchange rate is found
    if exchange_rate_found:
        exchange_rate_id = exchange_rate_found[0] # type: ignore # not used, keep just in case
        currency_source_id = exchange_rate_found[1] # type: ignore # not used, keep just in case
        currency_target_id = exchange_rate_found[2] # type: ignore
        exchange_rate_value = exchange_rate_found[3] # type: ignore
        exchange_rate_start_date_standardized = exchange_rate_found[4] # not used, need to find the exchange rate closest to date of amount to convert # type: ignore

    return exchange_rate_id, exchange_rate_value


# ==========================================
# Cross Currency Triangulation
# ==========================================

def cross_currency_triangulation(cursor, amount_to_convert, amount_to_convert_date, currency_to_convert_to, currency_to_convert_from):
    # Define variables
    amount_converted = None
    exchange_rate_id__A_to_C = None
    exchange_rate_id__B_to_C = None
    exchange_value_A_to_C = None
    exchange_value_B_to_C = None

    # 1. Extract all exchange rates where are the currency A (currency_to_convert_to) is present
    #-------------------------------------------------------------------
    cursor.execute("""
                    SELECT
                        currency_source_id,
                        currency_target_id
                    FROM
                        exchange_rate
                    WHERE
                        currency_source_id = %s
                        OR currency_target_id = %s
                    """, (currency_to_convert_to, currency_to_convert_to))

    # Fetch result
    exchange_rates_with_currency_A = cursor.fetchall()

    # Set of pairs of exchange rates with currency A
    set_of_pairs_currency_A = [(currency_id[0], currency_id[1]) for currency_id in exchange_rates_with_currency_A] # type: ignore


    # 2. Extract all exchange rates where are the currency B (currency_to_convert_from) is present
    #-------------------------------------------------------------------

    cursor.execute("""
                    SELECT
                        currency_source_id,
                        currency_target_id
                    FROM
                        exchange_rate
                    WHERE
                        currency_source_id = %s
                        OR currency_target_id = %s
                    """, (currency_to_convert_from, currency_to_convert_from))

    # Fetch result
    exchange_rates_with_currency_B = cursor.fetchall()

    # Set of pairs of exchange rates with currency B
    set_of_pairs_currency_B = [(currency_id[0], currency_id[1]) for currency_id in exchange_rates_with_currency_B] # type: ignore

    # if we found the the exchange rates with currency A and currency B
    if set_of_pairs_currency_A and set_of_pairs_currency_B:

        # 3. Find most frequent common currency C
        # (to construct the cross currency triangulation exchange rate between currency A and B)
        #---------------------------------------------------------------------------------------------------------------
        df_a = pandas.DataFrame(set_of_pairs_currency_A, columns=['first', 'second'])
        df_b = pandas.DataFrame(set_of_pairs_currency_B, columns=['first', 'second'])

        # find common values (all common currencies C) present both in exchange rates of currency A and currency B
        common_currencies = set(df_a.values.flatten()) & set(df_b.values.flatten())

        # if common currencies found
        if common_currencies:
            '''
            It is possible that there will be several "common" currencies. We will then have to choose one to construct our “cross-triangular” exchange rate. We will then choose the common currency which is the most frequent, because this way we will have more chance of finding an exchange rate as close as possible to our amount to be converted.
            '''
            # count occurence of each found common value
            occurrences = {}
            for currency in common_currencies:
                occurrences[currency] = df_a.values.flatten().tolist().count(currency) + df_b.values.flatten().tolist().count(currency)

            most_frequent_common_currency_string = max(occurrences, key=occurrences.get) # type: ignore
            most_frequent_common_currency = int(most_frequent_common_currency_string) # need to convert to integer to be able to query the database


            # 4. Calculate exchange value of currency A (currency_to_convert_to) to common currency C
            # -------------------------------------------------------------------------------------

            # Try to find the appropriate DIRECT exchange rate
            # (select by the currency to which we convert and by the closest date of exchange rate)
            exchange_rate_id__A_to_C, exchange_rate_value = find_exchange_rate_value(cursor, amount_to_convert_date, currency_to_convert_to, most_frequent_common_currency)

            # if we found the DIRECT exchange rate
            if exchange_rate_value:
                exchange_value_A_to_C = exchange_rate_value

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
                exchange_rate_id__A_to_C, exchange_rate_value = find_exchange_rate_value(cursor, amount_to_convert_date, most_frequent_common_currency, currency_to_convert_to)

                if exchange_rate_value:
                    exchange_value_A_to_C = 1 / exchange_rate_value # type: ignore



            # 5. Calculate exchange value of currency B (currency_to_convert_from) to common currency C
            # -------------------------------------------------------------------------------------

            # Try to find the appropriate DIRECT exchange rate
            # (select by the currency to which we convert and by the closest date of exchange rate)
            exchange_rate_id__B_to_C, exchange_rate_value = find_exchange_rate_value(cursor, amount_to_convert_date, currency_to_convert_from, most_frequent_common_currency)

            # if we found the DIRECT exchange rate
            if exchange_rate_value:
                exchange_value_B_to_C = exchange_rate_value

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
                exchange_rate_id__B_to_C, exchange_rate_value = find_exchange_rate_value(cursor, amount_to_convert_date, most_frequent_common_currency, currency_to_convert_from)

                if exchange_rate_value:

                    exchange_value_B_to_C = 1 / exchange_rate_value # type: ignore


            # 6. Construct the exchange rate value "currency A -> currency B"
            # (trought the excange rates "currency A -> currency C" and currency B -> currency C)
            # -------------------------------------------------------------------------------------
            """
            To calculate the cross-currency exchange rate between currency A and currency B through currency C, you typically use the following formula:
            Exchange Rate A/B = Exchange Rate A/C diveded by Exchange Rate B/C
            """

            if exchange_value_A_to_C and exchange_value_B_to_C:
                exchange_value_A_to_B = exchange_value_A_to_C / exchange_value_B_to_C

                # 7. Convert amount in currency B to amount in currency A
                # ---------------------------------------------------------

                amount_converted = amount_to_convert / exchange_value_A_to_B


    return amount_converted, exchange_rate_id__A_to_C, exchange_rate_id__B_to_C

