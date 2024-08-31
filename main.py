"""
Module: main.py

Description:
Main file for processing data from a text file and storing it into a SQL database.
In this file, we define the parameters to connect to our database and specify the text file we want to process.
The main function processes the text line by line with the aid of the function process_line from the file line_processor.
The processed data will be stored in a SQL database (the storing process is implemented in the file line_processor and other associated files).

To personalize this file for your own purpose:
- Change the database connection parameters where you want to store processed data. Please note, your database model must be the same as that used in this code to be usable by this Python code.
- Specify your spaCy model which you want to apply to your text. Be careful, your spaCy model must use the same label names to be usable by this Python code.
- Specify the path and name of the text you want to process.

"""

# Import libraries
# ------------------------------------------
import spacy # to text NLP processing

# Import custom functions
# ------------------------------------------
from database_config import connect_to_database
from main_handler_utils import process_text
from main_processor_line import process_line
# import database


# ==============================
# Functions
# ==============================

# Main function to process data
# ------------------------------------------
def main():

    # Define general variables
    # -------------------------
    nlp_model = spacy.load("training/training-itself/full/models/model-best") # load custom spaCy model
    input_data_path = 'test/data/raw/_all/' # path for text to process

    # Change manually then process each document
    # -------------------------------------------

    file_name = 'ASV_intr.ex.194' # file name without extension
    document_id = '23' # manually specify the id of document after insert the document into database



    # -------------------------------------------

    class_id = '1' # 1 = expense, 2 = revenue

    # Process text (get original text and text with rubrics)
    # -------------------------
    """
    The function process_text() adds rubrics and subrubrics markers (RUBRIC_NAME, SUBRUBRIC_NAME) to the original text. These markers are added depending on the number of line breaks between the text of paragraphs. These markers are necessary to recognize and process the rubrics and subrubrics names. Unfortunately, it can't be done in any other way because the original text is a plain text file, so we can't use any other formatting or style to mark the rubrics and subrubrics names in the original text.
    Also, this function returns the full original text (text_original) without rubrics and subrubrics markers. For now, the original text is not used anywhere, but we keep it just in case.

    For more details about this function, see the file with this function in the utils.py file.
    """
    text_original, text_with_rubrics = process_text(input_data_path, file_name)

    # Process each line
    # -------------------------
    process_line(connection, text_with_rubrics, nlp_model, document_id, class_id)

    print ("Text processed")

    # Close database connection
    connection.close()


# ==============================
# Processing
# ==============================

# connect to database
# -------------------------
connection = connect_to_database()

# process function main()
# -------------------------
if __name__ == "__main__":
    main()