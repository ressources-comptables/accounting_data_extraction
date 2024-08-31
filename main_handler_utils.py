"""
Module: main_handler_utils.py

Description:
This module contains various functions utilized for data processing tasks.

There are different blocks in this file, each corresponding to the treatment of a particular type of data.

1) Process original text:
   This block processes original text to add rubrics and subrubrics marks into the text. 
   These markers are necessary to recognize and process the rubric and subrubric names.

   Function(s):
   - process_text()

   Sub-function(s):
   - load_text()
   - add_rubric_subrubric_tag()

2) Extract folio (for table "line"):
   This function extracts the folio number from line text.

   Function(s):
   - folio_extraction()

3) Define type of line (for table "line"):
   This function defines the type of line based on the following possible types:
   - Transaction: Line with amounts.
   - RubricName: Line with rubric name.
   - SubrubricName: Line with subrubric name.
   - SumPage: Sum of folio ("summa pagina...").
   - SumRubric: Sum of rubric.
   - SumPeriod: Sum of some period.
   - SumTotal: Total sum (needs manual processing).
   - SumUndefined: Sum which can't be defined (line contains amount and the word "summa" but doesn't belong to any other sums).
   - Description: All other lines that don't correspond to any other type.

   Function(s):
   - assign_line_type()

4) Process rubric and subrubric names from text:
   This function processes the names of rubric and subrubric present in the text. 
   First, it extracts the name with the help of rubrics and subrubrics markers added previously and then standardizes this name.

   Function(s):
   - process_rubric_subrubric_from_text()

   Sub-function(s):
   - extract_name()
   - standardize_name()

5) Process rubric and subrubric to insert into database:
   Process and insert the rubric and subrubric names into the database. 
   First, check if the name already exists in the database; if yes, use it, if not insert the new one.

   Function(s):
   - process_rubric_subrubric_into_database()

   Sub-function(s):
   - check_and_insert_new_data()

6) Process product:
   Extract the product from text and insert them into the database. 
   The rate of successful recognition of products with NER is quite low (about 56%), so this data must undergo heavy post-treatment and manual verification.

   Function(s):
   - process_product()

7) Process participant:
   This function extracts the name of participants from text and inserts it into the "participant" table. 
   Usually, the extracted names are quite raw data and often the level of good recognition of person names is quite low (about 77%). 
   Note that the "participant" table is only a link between the "line" table and the "person" table. 
   So, during the post-treatment of the extracted names in the "participant" table, we need to process each extracted name, clean it, and insert it into the "person" table if this person does not already exist.

   Function(s):
   - process_participant()


Note: Each function within this module is documented separately within its respective definition.
"""


# Import libraries
# ------------------------------------------
import re # to work with regular expressions

# ==============================
# Process original text
# ==============================

def process_text(input_data_path, file_name):

    # Process original text
    # -----------------------
    """
    Description: 
    Replace occurrences of rubric and subrubric names with corresponding tags. Then, split the modified text into paragraphs based on a single line break.
    Define a list comprehension to iterate over lines containing rubric and subrubric tags.
    Join these lines into a single string, then split it into paragraphs based on a single line break.
    Filter out any empty paragraphs.
    Here "para" is the text of the obtained paragraph.

    Parameters (input):
    - input_data_path (str): 
        >>> Example: 
    - file_name (str, optional): 
        >>> Example: 

    Returns (output):
    - text_original (str): 
        >>> Example: 
    - text_with_rubrics (str): 
        >>> Example: 

    """
    def load_text(input_data_path, file_name):

        # Load original text to process
        text_original = open(f"{input_data_path}{file_name}.txt").read()

        # Add "rubrics" and "subrubrics" tags to text
        lines_with_rubric_subrubric_tag = add_rubric_subrubric_tag(text_original)
        
        # Add modified lines and split text
        text_with_rubrics = [para.strip() for para in '\n'.join(lines_with_rubric_subrubric_tag).split('\n') if para.strip()]

        return text_original, text_with_rubrics


    # Add "rubrics" and "subrubrics" tags to text
    # -------------------------------------------

    """
    Description:
    To identify the names of the rubrics and subrubrics we rely on the layout of the text. 
    In fact, rubric names have a blank line before and after them. 
    Subrubric names have one line before the text and, in our case, contain the word that begins with "solutio".
    It was not possible to identify these names directly and only with NER. 
    So, to be able to do this you have to pre-work the text and introduce additional identification tags: RUBRIC_NAME and SUBRUBRIC_NAME.

    """
    def add_rubric_subrubric_tag(text_original):
        lines = text_original.split('\n') # split text into a list of lines using the newline character ('\n') as the delimiter. Each element in the resulting list corresponds to a line of text.
        empty_line_pattern = re.compile(r'^\s*$') # create a regular expression pattern for matching empty lines
        lines_with_rubric_subrubric_tag = [] # initialize an empty list to store modified lines

        # loop to find lines with rubric and subrubric names and add appropriate tag
        for i, line in enumerate(lines):
            if i == 0 or i == len(lines) - 1: # need to keep the first and the last lines
                lines_with_rubric_subrubric_tag.append(line)
            elif empty_line_pattern.match(lines[i - 1]) and empty_line_pattern.match(lines[i + 1]):
                lines_with_rubric_subrubric_tag.append("RUBRIC_NAME " + line)
            elif empty_line_pattern.match(lines[i - 1]) and 'solutio' in line.lower():
                lines_with_rubric_subrubric_tag.append("SUBRUBRIC_NAME " + line)
            else:
                lines_with_rubric_subrubric_tag.append(line)

        return lines_with_rubric_subrubric_tag

    text_original, text_with_rubrics = load_text(input_data_path, file_name)

    return text_original, text_with_rubrics



# ============================================
# Extract folio (for table "line")
# ============================================
"""
Description:
Extract folio from text. E.g.: [f.34], [f.45v] etc.

"""

def folio_extraction(line):
    pattern = r'\[([^\]]*\d[^\]]*)\]' # extract all data contained within the brackets [] and which contains at least one digit (because we  also can have just a texte within the brackets [], e.g. [sic] )
    matches = re.findall(pattern, line)
    folio_extracted = ', '.join(matches) # return string, if many put comma between values
    return folio_extracted



# ============================================
# Define type of line (for table "line")
# ============================================

"""
This function defines the type of line based on the following possible types:
- Transaction: Line with amounts.
- RubricName: Line with rubric name.
- SubrubricName: Line with subrubric name.
- SumPage: Sum of folio ("summa pagina...").
- SumRubric: Sum of rubric.
- SumPeriod: Sum of some period.
- SumTotal: Total sum (needs manual processing).
- SumUndefined: Sum which can't be defined (line contains amount and the word "summa" but doesn't belong to any other sums).
- Description: All other lines that don't correspond to any other type.
"""

def assign_line_type(line, line_nlp):
    # Split the text into words
    words = line.split()

    if words:
        # Type: Sums
        # Check if the first word starts with "Summa"
        if words[0].startswith("Summa"):
            # Check for additional conditions and assign type accordingly
            if any(word.startswith("pagin") for word in words):
                return "6" # "SumPage"
            elif any(word.startswith("septima") for word in words):
                return "8" # "SumPeriod"
            elif any(word.startswith("summar") for word in words):
                return "7" # "SumRubric"
            else:
                return "5" # "SumUndefined"

        # Type: Rubric & Subrubric
        # Check if the words "RUBRIC_NAME" or "SUBRUBRIC_NAME" are presents in the text
        elif "RUBRIC_NAME" in words:
            return "3" # "RubricName"
        elif "SUBRUBRIC_NAME" in words:
            return "4" # "SubrubricName"

    # Type: Transaction
    # Check if line have the NER AMOUNT
    entities_amount = ', '.join(ent.text for ent in line_nlp.ents if ent.label_ == "AMOUNT")
    if entities_amount:
        return "2" # "Transaction"

    # Otherwise, return type "Description"
    return "1" # "Description"



# =====================================================
# Process rubric and subrubric names from text
# =====================================================

"""
This function processes the names of rubric and subrubric present in the text. 
First, it extracts the name with the help of rubrics and subrubrics markers added previously and then standardizes this name.
"""

def process_rubric_subrubric_from_text(line, category):

    # Extract full original name of rubric
    # -----------------------------------------
    def extract_name(line):
        # delete RUBRIC_NAME / SUBRUBRIC_NAME and folio [f...] from rubric/subrubric name and remove any leading or trailing whitespace characters

        # this construction is similar to if / elif, but more elegant
        category_patterns = {
            'rubric': 'RUBRIC_NAME',
            'subrubric': 'SUBRUBRIC_NAME'
        }
        pattern = category_patterns.get(category)

        name_extracted = re.sub(rf'{pattern} |\[([^\]]*\d[^\]]*)\]', '', line).strip()
        return name_extracted


    # Extract from full original name of (sub)rubric the standardized name
    # ---------------------------------------------------------------
    def standardize_name(name_extracted):
        
        if category == 'rubric':
            # Regular expression pattern to match the text after "pro"
            pattern = re.compile(r'\bpro\b\s*(.*)')
        elif category == 'subrubric':
            # Regular expression pattern to match all words before "solutio"
            pattern = re.compile(r'(\b\w+\b)\s*solutio', re.IGNORECASE)

        # Find the match in the text
        match = pattern.search(name_extracted)

        if match:
            if category == 'rubric':
                name_standardized = match.group(1)
            elif category == 'subrubric':
                name_standardized = match.group(1)+ " solutio"
        else:
            name_standardized = name_extracted

        # Extract the matched text
        return name_standardized.strip()

    name_extracted = extract_name(line)
    name_standardized = standardize_name(name_extracted)

    return name_extracted, name_standardized



# =====================================================
# Process rubric and subrubric to insert into database
# =====================================================

"""
Process and insert the rubric and subrubric names into the database. 
First, check if the name already exists in the database; if yes, use it, if not insert the new one.

"""

def process_rubric_subrubric_into_database(cursor, name_extracted, name_standardized, category):

    def check_and_insert_new_data(cursor, name, category, data_type):

        # Check if the name exist in the table
        cursor.execute(f"SELECT {category}_{data_type}_id FROM {category}_{data_type} WHERE {category}_name_{data_type} = %s", (name,))
        existing_id = cursor.fetchone()

        if existing_id:
            current_id = existing_id[0]
        else:
            # Insert the new name into the table if name doesnt exist already
            cursor.execute(f"INSERT INTO {category}_{data_type} ({category}_name_{data_type}) VALUES (%s)", (name,))
            current_id = cursor.lastrowid  # Retrieve auto-incremented ID

        return current_id

    current_extracted_id = check_and_insert_new_data(cursor, name_extracted, category, 'extracted')
    current_standardized_id = check_and_insert_new_data(cursor, name_standardized, category, 'standardized')

    # Update the (sub)rubric_extracted row with the (sub)rubric_standardized_id
    cursor.execute(f"UPDATE {category}_extracted SET {category}_standardized_id = %s WHERE {category}_extracted_id = %s", (current_standardized_id, current_extracted_id))

    return current_extracted_id


"""
The code above is a short version of the code that follows.
Just keep it in case.

# ------------------------------------------------------------------
# 1. Rubrics names
# ------------------------------------------------------------------
if line_type == "3":

    # Extract & Standardize rubric name from text
    rubric_name_extracted, rubric_name_standardized = process_rubric_name(line)


    # 1.1 Insert extracted rubric information into rubric_extracted table.
    # ------------------------------------------------------------------
    # Check if the rubric_name_extracted already exists in the rubric_extracted table
    cursor.execute("SELECT rubric_extracted_id FROM rubric_extracted WHERE rubric_name_extracted = %s", (rubric_name_extracted,))
    existing_rubric_extracted_id = cursor.fetchone()

    if existing_rubric_extracted_id:
        rubric_extracted_id = existing_rubric_extracted_id[0]
    else:
        # Insert the new rubric_name_extracted into the rubric_extracted table
        cursor.execute("INSERT INTO rubric_extracted (rubric_name_extracted) VALUES (%s)", (rubric_name_extracted,))
        rubric_extracted_id = cursor.lastrowid  # Retrieve auto-incremented ID


    # 1.2 Insert standardized rubric information into rubric_standardized table.
    # ------------------------------------------------------------------------------
    # Check if the rubric_name_standardized already exists in the rubric_standardized table
    cursor.execute("SELECT rubric_standardized_id FROM rubric_standardized WHERE rubric_name_standardized = %s", (rubric_name_standardized,))
    existing_rubric_standardized_id = cursor.fetchone()

    if existing_rubric_standardized_id:
        rubric_standardized_id = existing_rubric_standardized_id[0]
    else:
        # Insert the new rubric_name_standardized into the rubric_standardized table
        cursor.execute("INSERT INTO rubric_standardized (rubric_name_standardized) VALUES (%s)", (rubric_name_standardized,))
        rubric_standardized_id = cursor.lastrowid  # Retrieve auto-incremented ID

    # 1.3. Update the rubric_extracted row with the rubric_standardized_id
    # ------------------------------------------------------------------
    cursor.execute("UPDATE rubric_extracted SET rubric_standardized_id = %s WHERE rubric_extracted_id = %s", (rubric_standardized_id, rubric_extracted_id))


# ------------------------------------------------------------------
# 2. Subrubrics names
# ------------------------------------------------------------------
if line_type == "4":

    # Extract & Standardize surubric name from text
    subrubric_name_extracted, subrubric_name_standardized = process_subrubric_name(line)


    # 2.1 Insert extracted subrubric information into subrubric_extracted table.
    # ------------------------------------------------------------------
    # Check if the subrubric_name_extracted already exists in the subrubric_extracted table
    cursor.execute("SELECT subrubric_extracted_id FROM subrubric_extracted WHERE subrubric_name_extracted = %s", (subrubric_name_extracted,))
    existing_subrubric_extracted_id = cursor.fetchone()

    if existing_subrubric_extracted_id:
        subrubric_extracted_id = existing_subrubric_extracted_id[0]
    else:
        # Insert the new subrubric_name_extracted into the subrubric_extracted table
        cursor.execute("INSERT INTO subrubric_extracted (subrubric_name_extracted) VALUES (%s)", (subrubric_name_extracted,))
        subrubric_extracted_id = cursor.lastrowid  # Retrieve auto-incremented ID


    # 2.2 Insert standardized subrubric information into subrubric_standardized table.
    # ------------------------------------------------------------------------------
    # Check if the subrubric_name_standardized already exists in the subrubric_standardized table
    cursor.execute("SELECT subrubric_standardized_id FROM subrubric_standardized WHERE subrubric_name_standardized = %s", (subrubric_name_standardized,))
    existing_subrubric_standardized_id = cursor.fetchone()

    if existing_subrubric_standardized_id:
        subrubric_standardized_id = existing_subrubric_standardized_id[0]
    else:
        # Insert the new subrubric_name_standardized into the subrubric_standardized table
        cursor.execute("INSERT INTO subrubric_standardized (subrubric_name_standardized) VALUES (%s)", (subrubric_name_standardized,))
        subrubric_standardized_id = cursor.lastrowid  # Retrieve auto-incremented ID

    # 2.3 Update the subrubric_extracted row with the subrubric_standardized_id
    # ------------------------------------------------------------------
    cursor.execute("UPDATE subrubric_extracted SET subrubric_standardized_id = %s WHERE subrubric_extracted_id = %s", (subrubric_standardized_id, subrubric_extracted_id))
"""



# =====================================================
# Process product
# =====================================================

"""
Extract the product from text and insert them into the database. 
The rate of successful recognition of products with NER is quite low (about 56%), so this data must undergo heavy post-treatment and manual verification.

"""

def process_product(cursor, line_id, line_nlp):
    # initialize variables
    products_extracted = []
    count_products = 0
    product_uncertainty = None

    # extract named entity "PRODUCT" from text
    for ent in line_nlp.ents:
        # Checking if the entity has the label "PRODUCT"
        if ent.label_ == "PRODUCT":
            products_extracted.append(ent.text)
            count_products += 1

    if count_products > 1:
        product_uncertainty = 1

    for product in products_extracted:
        product_extracted = product
        cursor.execute("INSERT INTO product (line_id, product_extracted, product_uncertainty) VALUES (%s, %s, %s)", (line_id, product_extracted, product_uncertainty,))



# =====================================================
# Process participant
# =====================================================

"""
This function extracts the name of participants from text and inserts it into the "participant" table. 
Usually, the extracted names are quite raw data and often the level of good recognition of person names is quite low (about 77%). 
Note that the "participant" table is only a link between the "line" table and the "person" table. 
So, during the post-treatment of the extracted names in the "participant" table, we need to process each extracted name, clean it, and insert it into the "person" table if this person does not already exist.
"""

def process_participant (cursor, line_id, line_nlp, participant_previous):
    
    # Initialize variables
    participants_extracted = []
    count_participants = 0
    participant_extracted = None
    participant_name_extracted = None
    participant_role_extracted = None
    additional_participant = None
    participant_uncertainty = None


    # extract named entity "PERSON_PAYEE" from text
    for ent in line_nlp.ents:
        # Checking if the entity has the label "PRODUCT"
        if ent.label_ == "PERSON_PAYEE":
            participants_extracted.append(ent.text)
            count_participants += 1

    # Process each payee_extracted
    for participant_extracted in participants_extracted:

        # Check if participant is not "socio"
        if not participant_extracted.lower().startswith("soci"):

            # Check if the same participant as previously
            if participant_extracted.lower().startswith(("eidem", "eisdem")) and participant_previous:
                participant_extracted = participant_previous

            # Process participant
            # --------------------------------
                
            # Participant name
            participant_name_extracted_list = re.findall(r'\b(?![a-z])[a-zA-Z]+\b(?:\W*)*(?:\s*[a-z]{2,})*(?:\s*\b(?![a-z])[a-zA-Z]+)*', participant_extracted)
            participant_name_extracted = participant_name_extracted_list[0] if participant_name_extracted_list else None
            if len(participant_name_extracted_list) != 1:
                participant_uncertainty = "1"

            # participant role
            participant_role_extracted_list = re.findall(r'\b[a-z]{3,}(?:\s*[a-z]{3,})*', participant_extracted)
            participant_role_extracted = ", ".join(participant_role_extracted_list)


            # check if there is a mention of "partners" [socio] anywhere in the text (not only in the beggining)
            # if "socio" in participant_extracted:
            additional_participant_list = re.findall(r'\b(socio).*', participant_extracted)
            additional_participant = ", ".join(additional_participant_list)

            person_function_id = "1"

            if participant_name_extracted:
                cursor.execute("INSERT INTO participant (line_id, participant_extracted, participant_name_extracted, participant_role_extracted, additional_participant, person_function_id, participant_uncertainty) VALUES (%s, %s, %s, %s, %s, %s, %s)", (line_id, participant_extracted, participant_name_extracted, participant_role_extracted, additional_participant, person_function_id, participant_uncertainty,))

            participant_previous = participant_extracted

    return participant_previous

