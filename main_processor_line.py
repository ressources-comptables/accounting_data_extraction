"""
Module: main_processor_line.py

Description:
This file contains a main function to process the lines of text. 
Each possible part and element of the line is treated here (for example, rubric names, dates, folio numbers, amounts, etc.). 
So this function serves as an entry point to all other functions to treat each different type of data that a line can contain. 
For this reason, all other functions are appended to this file (the functions from files: utils.py, amount_handler.py, and date_handler.py).
"""

# Import libraries
# ------------------------------------------

# Import custom functions
# ------------------------------------------
from main_handler_utils import folio_extraction, assign_line_type, process_rubric_subrubric_from_text, process_rubric_subrubric_into_database, process_product, process_participant
from main_handler_amount import process_amount
from main_handler_date import process_date_into_database


# ============================================
# Extract data for table "line"
# (+ tables: rubric_extracted, rubric_standardized, subrubric_extracted, subrubric_standardized, date)
# ============================================

def process_line(connection, text_with_rubrics, nlp_model, document_id, class_id):
    # Initialize an empty list to store line data
    data_line = []
    cursor = connection.cursor(buffered=True)

    # Define variables
    folio_previous = ""
    participant_previous = ""
    rubric_extracted_id = None
    subrubric_extracted_id = None
    # rubric_name_extracted = None
    # subrubric_name_extracted = None
    previous_date_standardized = '1000-01-01' # default date

    # ------------------------------------------------------------------
    # Process each line of text
    # ------------------------------------------------------------------
    for i, line in enumerate(text_with_rubrics):

        # Process spaCy on the text. So we have two variables: "para" which is a original text and "doc" which is a text processed by spaCy to work with NER
        line_nlp = nlp_model(line)

        # ------------------------------------------------------------------
        # Line number
        # ------------------------------------------------------------------
        line_number = i + 1

        # ------------------------------------------------------------------
        # Type of line
        # ------------------------------------------------------------------
        line_type = assign_line_type(line, line_nlp)

        # ------------------------------------------------------------------
        # Folio
        # ------------------------------------------------------------------
        """
        Extract the current folio number from the text. If no folio is found, retain the previous value. If the previous value contains two folio numbers separated by a comma (e.g., f.34, f34v), take only the second one. This adjustment is made because a line might reference multiple folios (f.34, f.34v), but logically, the following line should belong only to the last mentioned folio (f.34v).
        Python doesn't support indexing the last element directly with [last], but we can use [-1] to access
        the last element of a list.
        """
        folio_current = folio_extraction(line) or (folio_previous.split(', ')[-1] if ',' in folio_previous else folio_previous)


        # ------------------------------------------------------------------
        # 1. Rubrics names
        # ------------------------------------------------------------------
        if line_type == "3": # = "RubricName"

            # Extract & Standardize rubric name from text
            rubric_name_extracted, rubric_name_standardized = process_rubric_subrubric_from_text(line, 'rubric')
            rubric_extracted_id = process_rubric_subrubric_into_database(cursor, rubric_name_extracted, rubric_name_standardized, 'rubric')

        # ------------------------------------------------------------------
        # 2. Subrubrics names
        # ------------------------------------------------------------------
        if line_type == "4": # = "SubrubricName"

            # Extract & Standardize surubric name from text
            subrubric_name_extracted, subrubric_name_standardized = process_rubric_subrubric_from_text(line, 'subrubric')
            subrubric_extracted_id = process_rubric_subrubric_into_database(cursor, subrubric_name_extracted, subrubric_name_standardized, 'subrubric')


        # ------------------------------------------------------------------
        # Line text
        # ------------------------------------------------------------------
        # to obtain the original text of line we need to remove the rubric and subrubric identification tags
        line_text = line.replace("SUBRUBRIC_NAME ", '').replace("RUBRIC_NAME ", '').strip() 

        # ------------------------------------------------------------------
        # Date
        # ------------------------------------------------------------------
        date_id, previous_date_standardized = process_date_into_database(cursor, line, line_type, line_nlp, previous_date_standardized)


        # ------------------------------------------------------------------
        # Construct final full data for table "line"
        # ------------------------------------------------------------------
        # Append (line_number, line_text) tuple to data_line list
        # data_line.append((document_id, class_id, line_number, line_type, folio_current, rubric_extracted_id, subrubric_extracted_id, line_text, date_id))

        # Insert line data into database
        cursor.execute("INSERT INTO line (document_id, class_id, rubric_extracted_id, subrubric_extracted_id, line_type_id, date_id, line_number, folio, text) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (document_id, class_id, rubric_extracted_id, subrubric_extracted_id, line_type, date_id, line_number, folio_current, line_text,))
        line_id = cursor.lastrowid  # Retrieve auto-incremented ID


        # ------------------------------------------------------------------
        # Process connected tables
        # ------------------------------------------------------------------

        # Process "product" table
        process_product(cursor, line_id, line_nlp)

        # Process amounts
        if line_type in ["2", "6", "8", "7", "5"]:
            # = "Transaction", "SumPage", "SumPeriod", "SumRubric", "SumUndefined"

            process_amount(cursor, line, line_id)

        # Process participants
        participant_previous = process_participant(cursor, line_id, line_nlp, participant_previous)

        # ------------------------------------------------------------------
        # Update variables
        # -----------------------------------
        folio_previous = folio_current
        

    # ------------------------------------------------------------------
    # Commit the transaction
    # -----------------------
    connection.commit()
    cursor.close()

    # return data_line

