
"""
Module: main_handler_date.py

Description:
This module provides functions for processing extracted date information from raw text to standardized date formats with uncertainty variables. It includes functions for extracting Roman numerals, converting them to Arabic numerals, finding and standardizing days, months, and years, as well as processing dates for database insertion and handling durations.

Functions:
1. process_date(dates_extracted, previous_date_standardized="1000-01-01"):
   - Description: Process a list of extracted dates to produce standardized dates with uncertainty variable.
   - Parameters: dates_extracted (list), previous_date_standardized (str, optional)
   - Returns: dates_processed (list)

2. standardize_date(date_extracted, previous_date_standardized='1000-01-01'):
   - Description: Standarize a date extracted from text to YYYY-MM-DD format.
   - Parameters: date_extracted (str), previous_date_standardized (str, optional)
   - Returns: date_standardized (str), date_uncertainty (int)

3. extract_roman_numerals(date_extracted):
   - Description: Extract Roman numerals from provided text.
   - Parameters: date_extracted (str)
   - Returns: roman_numerals (list)

4. convert_roman_to_arabic(roman_numerals):
   - Description: Convert a list of Roman numerals to Arabic numerals.
   - Parameters: roman_numerals (list)
   - Returns: arabic_numerals (list, int), date_uncertainty (int)

5. find_day(date_extracted, arabic_numerals, previous_date_standardized='1000-01-01'):
   - Description: Find the day mentioned in text or in Arabic numerals.
   - Parameters: date_extracted (str), arabic_numerals (list, int), previous_date_standardized (str, optional)
   - Returns: day (str), day_count (int)

6. find_year(arabic_numerals, previous_date_standardized='1000-01-01'):
   - Description: Find the year mentioned in Arabic numerals.
   - Parameters: arabic_numerals (list, int), previous_date_standardized (str, optional)
   - Returns: year (str), year_count (int)

7. find_month(date_extracted, previous_date_standardized='1000-01-01'):
   - Description: Find the month mentioned in text.
   - Parameters: date_extracted (str), previous_date_standardized (str, optional)
   - Returns: month (str), month_count (int)

8. process_date_into_database(cursor, line, line_type, line_nlp, previous_date_standardized):
   - Description: Process date to insert into database.
   - Parameters: cursor, line, line_type, line_nlp, previous_date_standardized

9. process_duration(line, start_date_standardized, start_date_uncertainty, end_date_uncertainty):
   - Description: Process duration to insert into database.
   - Parameters: line, start_date_standardized, start_date_uncertainty, end_date_uncertainty

10. extract_preceding_words(line, target_words, excerpt_size):
    - Description: Extract preceding words before mention of a duration.
    - Parameters: line (str), target_words (list), excerpt_size (int)
    - Returns: preceding_words (list, str)
"""

# Import libraries
# ------------------------------------------
import re # to work with regular expressions
import calendar # to work with calendars date
from datetime import datetime, timedelta # to work with datetime objects (to add or substruct days from given date)

# ==============================
# Date Full Processing 
# (from raw original text to standardized date with certanity variable)
# ==============================

"""
Description:
Process a list of extracted dates to produce standardized dates with uncertainty variable.

This function iterates over a list of extracted dates, processes each date individually,
and produces a list of dictionaries containing the original extracted date, the standardized
date in YYYY-MM-DD format, and a variable indicating any uncertainty during the process.

Parameters (input):
- dates_extracted (list): A list of strings containing extracted date information.
    >>> Example: dates_extracted = ['Anno Domini millesimo CCCXVI, die XII mensis augusti', 'die X mensis augusti', 'eadem die', 'die XVIII martii']
- previous_date_standardized (str, optional): The previously standardized date (default is '1000-01-01' if unknown).
    >>> Example: previous_date_standardized = '1000-01-01'

Returns (output):
- dates_processed (list): A list of dictionaries containing processed date information.
    Each dictionary has the following keys:
        - 'date_extracted': The original extracted date.
        - 'date_standardized': The standardized date in YYYY-MM-DD format.
        - 'date_uncertainty': A variable indicating the level of uncertainty (0 if no error occurred, 1 if there was an error). Possibles errors: if no date found, if "eadem die", if non valid letter in roman numerals, if in the same text there are more than 1 mention of day, month or year.
    >>> Example: dates_processed = [{'date_extracted': 'Anno Domini millesimo CCCXVI, die XII mensis augusti', 'date_standardized': '1316-08-12', 'date_uncertainty': 0}, {'date_extracted': 'die KX mensis augusti', 'date_standardized': '1316-08-12', 'date_uncertainty': 1}, {'date_extracted': 'eadem die', 'date_standardized': '1316-08-12', 'date_uncertainty': 1}, {'date_extracted': 'die XVIII martii', 'date_standardized': '1316-03-18', 'date_uncertainty': 0}]
"""

def process_date(dates_extracted, previous_date_standardized="1000-01-01"):
    ## VARIABLES
    dates_processed = []

    # if line have the date(s)
    if dates_extracted:

        # process each date
        for date_extracted in dates_extracted:
            # Initialize variables
            date_standardized = None
            date_uncertainty = 0

            # if date has "eadem die" or "dicta die", use the previous date
            exclude_keywords = {"eadem die", "dicta die"}
            if any(keyword.lower() in date_extracted.lower() for keyword in exclude_keywords):
                date_standardized = previous_date_standardized
                date_uncertainty += 1
            # if not, process DATE and calculate new values
            else:
                date_standardized, date_uncertainty = standardize_date(date_extracted, previous_date_standardized)

            # to pass previous date through iterination
            previous_date_standardized = date_standardized

            dates_processed.append({
                "date_extracted": date_extracted,
                "date_standardized": date_standardized,
                "date_uncertainty": date_uncertainty
            })

    # there are no dates in the line
    else:
        dates_processed.append({
            "date_extracted": None,
            "date_standardized": previous_date_standardized,
            "date_uncertainty": 1
        })

    return dates_processed


# ==============================
# Date standarization
# ==============================

"""
Description:
Standarize a date extracted from text.
This function takes a text containing a date and produces a standardized date
in the format YYYY-MM-DD with an uncertainty variable to signal any errors. 
The standarization process involves several steps including extracting Roman 
numerals, converting them to Arabic numerals, finding the day, month, and year 
mentions, and resolving any uncertainties.

Parameters (input):
- date_extracted (str): The text containing the date information.
    >>> Example: date_extracted = 'Anno Domini millesimo CCCXVI, die XII mensis augusti'
- previous_date_standardized (str, optional): The previously standardized date (default is '1000-01-01' if unknown).
    >>> Example: previous_date_standardized = '1000-01-01'

Returns (output):
- date_standardized (str): The standardized date in YYYY-MM-DD format.
    >>> Example: date_standardized = '1316-08-12'
- date_uncertainty (int): A variable indicating the level of uncertainty:
       - 0 if no error occurred during standarization.
       - 1 if there was an error (e.g., no date found, invalid Roman numerals, multiple mentions of day, month, or year in the same text).
    >>> Example: date_uncertainty = 1

"""


def standardize_date(date_extracted, previous_date_standardized='1000-01-01'):

    # 1. Extract Roman Numerals
    roman_numerals = extract_roman_numerals(date_extracted)

    # 2. Convert Roman to Arabic
    arabic_numerals, date_uncertainty = convert_roman_to_arabic(roman_numerals)

    # 3. Find a day
    day, day_count = find_day(date_extracted, arabic_numerals, previous_date_standardized)

    # 4. Find a year
    year, year_count = find_year(arabic_numerals, previous_date_standardized)

    # 5. Find a month
    month, month_count = find_month(date_extracted, previous_date_standardized)

    # 6. Set up the uncertain variable if there are several mentions of day, month
    # for year the warning only there are more than one mention,
    # otherwise we will have it all the time and it will lose its meaning, because the majority of lines do not have the year (year_count == 0)
    # Be careful, if there are many values for day, month or year we keep only a last found ones (beacause we want to construt a valid date in format YYYY-MM-DD)
    # If need to keep all values, feel free to adapt the code to your need

    if day_count != 1 or year_count > 1 or month_count != 1:
        date_uncertainty += 1  # if we have zero or more than one mentions for day, month or year, so, Houston, we have a problem

    # 7. Date standarization to SQL
    date_standardized = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    return date_standardized, date_uncertainty


# ==============================
# Extract roman numerals
# ==============================

"""
Description:
Extracts Roman numerals from the provided text.

Parameters (input):
- date_extracted (str): The text from which Roman numerals are to be extracted.
    >>> Example: date_extracted = 'Anno Domini millesimo CCCXVI, die XII mensis augusti'

Returns (output):
- roman_numerals (list): A list containing the strings with extracted Roman numerals.
    >>> Example: roman_numerals = ['CCCXVI', 'XII']
"""

def extract_roman_numerals(date_extracted):
    # Use the \b word boundary and a permissive Roman numeral pattern
    roman_numerals = re.findall(r'[IVXLCDM]+(?:\s[IVXLCDM]+)*(?![a-z])', date_extracted) # split complex number into parts
    return roman_numerals


# ==========================================
# Convert roman numerals to arabic numerals
# ==========================================

"""
Description:
Converts a list of Roman numerals to Arabic numerals.

Parameters (input):
- roman_numerals (list, str): A list of strings with Roman numerals.
    >>> Example: roman_numerals = ['CCCXVI', 'XII']

Returns (output):
- arabic_numerals (list, int): A list of integers with Arabic numerals converted from the Roman numerals. Be careful, it is nor more string values, this become a numerical (integer) values.
    >>> Example: arabic_numerals = [316, 12]
- date_uncertainty (int): A variable indicating the level of uncertainty:
        - 0 if no error occurred during conversion.
        - 1 if there was an error of conversation (invalid Roman numerals).
    >>> Example: date_uncertainty = 0
"""


def convert_roman_to_arabic(roman_numerals):
    roman_dict = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    arabic_numerals = [] # to store all converted arabic numerals
    uncertainty_conversion = 0

    for roman_numeral in roman_numerals:
        arabic_numeral = 0
        prev_value = 0
        for char in reversed(roman_numeral):
            if char not in roman_dict:  # Check if the character is a valid Roman numeral
                uncertainty_conversion += 1
                continue # if this function is used separetly, then it will ignore non valid roman numeral and continue
            value = roman_dict[char]
            if value < prev_value:
                arabic_numeral -= value
            else:
                arabic_numeral += value
            prev_value = value

        arabic_numerals.append(arabic_numeral)

    return arabic_numerals, uncertainty_conversion


# ============================================
# Find day from text and / or arabic numerals
# ============================================

"""
Description:
Finds the day mentioned in the text or in the Arabic numerals. 
If no day is found, it uses the day extracted from the previous date.


Parameters (input):
- date_extracted (str): The text from which the day is to be found.
    >>> Example: date_extracted = 'Anno Domini millesimo CCCXVI, die XII mensis augusti'
- arabic_numerals (list, int): A list of integers with Arabic numerals converted from the Roman numerals. Be careful, it is nor more string values, this become a numerical (integer) values.
    >>> Example: arabic_numerals = [316, 12]
- previous_date_standardized (str, optional): The previously standardized date (default is '1000-01-01' if unknown).
    >>> Example: previous_date_standardized = '1000-01-01'

Returns (output):
- day (str): The found day.
    >>> Example: day = '12'
- day_count (int): The count of days found. This is used to define uncertainty; if more than one day is found, it is considered abnormal and raises a warning.
    >>> Example: day_count = 1

"""


# Find a day
def find_day(date_extracted, arabic_numerals, previous_date_standardized='1000-01-01'):
    # day = 'O1' # default day
    day = previous_date_standardized.split('-')[2]  # default day, if no day found
    day_count = 0
    found_valid_day_in_arabic_values = False  # Flag to track if a valid day in arabic values is found


    # to find the month and the year to calculate the correct day number for mention "ultima"
    month, month_count = find_month(date_extracted, previous_date_standardized)
    year, year_count = find_year(arabic_numerals, previous_date_standardized)

    # Convert month and year to an integer
    month_int = int(month)
    year_int = int(year)

    # calculate the last day of month (and convert it to string)
    num_days_in_month = str(calendar.monthrange(year_int, month_int)[1])


    # first, processing the arabic values
    for arabic_numeral in arabic_numerals:
        if isinstance(arabic_numeral, int) and 1 <= arabic_numeral <= 31:
            day = str(arabic_numeral)
            day_count += 1  # check if we have more than one day mention
            found_valid_day_in_arabic_values = True  # Set the flag to True

    # if there are no valid day value found in the arabic values, look for value expressed in letters or with special writing 
    # to start, create the map of values
    if not found_valid_day_in_arabic_values:
        keyword_to_day = {
            "prima": "01",
            "secunda": "02",
            "tertia": "03",
            "quarta": "04",
            "quinta": "05",
            "septima": "07",
            "nona": "09",
            "decima": "10",
            "ultima": num_days_in_month,
            "XXIIII": "24",
            "XIIII": "14",
            "IIII": "04"
        }

        # look for mentionned values in the initial text of date
        for keyword, value in keyword_to_day.items():
            if keyword in date_extracted:
                day = value
                day_count += 1  # Check if we have more than one day mention

    return day, day_count



# ============================================
# Find year from arabic numerals
# ============================================

"""
Description:
Finds the year mentioned in the Arabic numerals.
If no year is found, it uses the year extracted from the previous date.

Parameters:
- arabic_numerals (list, int): A list of integers with Arabic numerals converted from the Roman numerals. Be careful, it is nor more string values, this become a numerical (integer) values.
    >>> Example: arabic_numerals = [316, 12]
- previous_date_standardized (str, optional): The previously standardized date (default is '1000-01-01' if unknown).
    >>> Example: previous_date_standardized = '1000-01-01'

Returns:
- year (str): The found year.
    >>> Example: year = '1316'
- year_count (int): The count of years found. This is used to define uncertainty; if more than one year is found, it is considered abnormal and raises a warning.
    >>> Example: year_count = 1
"""


# Find a year
def find_year(arabic_numerals, previous_date_standardized='1000-01-01'):
    year = previous_date_standardized.split('-')[0]
    year_count = 0

    for arabic_numeral in arabic_numerals:
        if isinstance(arabic_numeral, int) and arabic_numeral >= 1000:
            # for case like "Anno Domini MCCCXVII"
            year = str(arabic_numeral)
            year_count += 1  # check if we have more than one year mention
        elif isinstance(arabic_numeral, int) and 100 <= arabic_numeral <= 999:
            # for case like "Anno Domini millesimo CCCXVI"
            year = str(arabic_numeral + 1000)
            year_count += 1  # check if we have more than one year mention

    return year, year_count




# ============================================
# Find month from arabic numerals
# ============================================

"""
Description:
Finds the month mentioned in the text.
If no month is found, it uses the month extracted from the previous date.

Parameters:
- date_extracted (str): The text from which the month is to be found.
    >>> Example: date_extracted = 'Anno Domini millesimo CCCXVI, die XII mensis augusti'
- previous_date_standardized (str, optional): The previously standardized date (default is '1000-01-01' if unknown).
    >>> Example: previous_date_standardized = '1000-01-01'

Returns:
- month (str): The found month.
    >>> Example: month = '08'
- month_count (int): The count of months found. This is used to define uncertainty; if more than one month is found, it is considered abnormal and raises a warning.
    >>> Example: month_count = 1

"""


# Find a month
def find_month(date_extracted, previous_date_standardized='1000-01-01'):
    # month = 'O1' # default month
    month = previous_date_standardized.split('-')[1]  # default month, if no month found
    month_count = 0

    month_mapping = {
        'januar': '01',
        'februar': '02',
        'febroar': '02',
        'mart': '03',
        'april': '04',
        'mad': '05',
        'maii': '05',
        'jun': '06',
        'jul': '07',
        'august': '08',
        'septembr': '09',
        'octobr': '10',
        'novembr': '11',
        'decembr': '12',
    }

    # Split the text into words
    words = date_extracted.split()

    # Iterate through words
    for word in words:
        # Check if any month name is a prefix of the word
        for month_name, month_number in month_mapping.items():
            if word.lower().startswith(month_name):
                month_count += 1
                month = month_number

    return month, month_count



##############################################
# INSERT INTO DATABASE
##############################################



# =====================================================
# Process date to insert into database
# =====================================================

def process_date_into_database(cursor, line, line_type, line_nlp, previous_date_standardized):

    # Initialize variables for start and end dates
    # start_date_extracted = None
    # start_date_standardized = None
    # start_date_uncertainty = None

    # Initialize variables for end dates (because we always have start date as default date = 1000-01-01)
    end_date_extracted = None
    end_date_standardized = None
    end_date_uncertainty = None

    # Initialize variable for duration if there is no duration found (the line is no "SumPeriod" type)
    duration_extracted = None
    duration_standardized_in_days = None
    duration_uncertainty = None

    # Initialize variable for date_id if there are no dates
    date_id = None

    # Extract all Data NER entity
    dates_extracted = []

    for ent in line_nlp.ents:
        # Checking if the entity has the label "DATE"
        if ent.label_ == "DATE":
            dates_extracted.append(ent.text)

    # process extracted date(s)
    dates_processed = process_date(dates_extracted, previous_date_standardized)

    # Check if any dates were processed
    # if dates_processed:

    # Get start date (if no date found in text, it will take a default value = 1000-01-01)
    start_date_extracted = dates_processed[0]["date_extracted"]
    start_date_standardized = dates_processed[0]["date_standardized"]
    start_date_uncertainty = dates_processed[0]["date_uncertainty"]

    # If there are more than one date, we will take the last one as end date
    if len(dates_processed) > 1:
        end_date_extracted = dates_processed[-1]["date_extracted"]
        end_date_standardized = dates_processed[-1]["date_standardized"]
        end_date_uncertainty = dates_processed[-1]["date_uncertainty"]

    # Check if the line is "SumPeriod" and if so, determine the duration and recalculate start and end dates
    if line_type == "8": # = "SumPeriod"
        start_date_standardized, start_date_uncertainty, end_date_standardized, end_date_uncertainty, duration_extracted, duration_standardized_in_days, duration_uncertainty = process_duration (line, start_date_standardized, start_date_uncertainty, end_date_standardized, end_date_uncertainty)

    # Insert data into database
    cursor.execute("INSERT INTO date (start_date_extracted, start_date_standardized, start_date_uncertainty, end_date_extracted, end_date_standardized, end_date_uncertainty, duration_extracted, duration_standardized_in_days, duration_uncertainty) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (start_date_extracted, start_date_standardized, start_date_uncertainty, end_date_extracted, end_date_standardized, end_date_uncertainty, duration_extracted, duration_standardized_in_days, duration_uncertainty,))
    date_id = cursor.lastrowid  # Retrieve auto-incremented ID


    # UPDATE VARIABLES
    if end_date_standardized:
        previous_date_standardized = end_date_standardized
    else:
        previous_date_standardized = start_date_standardized

    return date_id, previous_date_standardized



# =====================================================
# Process duration to insert into database
# =====================================================

def process_duration (line, start_date_standardized, start_date_uncertainty, end_date_standardized, end_date_uncertainty):

    # Variables
    # ------------------------------------------------------
    # set default value
    duration_uncertainty = 0
    conversion_uncertainty = 0
    duration_extracted = None
    duration_standardized_in_days = None
    duration_standardized_in_weeks = None

    # Define target words for week (singular and plural)
    week_singular = ["septimana", "septimane", "septimanam", "septimanae"]
    week_plural = ["septimanas", "septimanarum", "septimanis", "septimarum"]

    # Excerpt size in words
    excerpt_size = 3

    # Parse the string into a datetime object to be able to make calculation with date
    # start_date_standardized = "1000-01-01"
    if start_date_standardized:
        start_date_standardized_datetime = datetime.strptime(start_date_standardized, "%Y-%m-%d")

        """
        # To handle possible error in datetime conversion - use if needed
        # use "try" and "except" to handle error for invalid date when convert to datetime object
        try:
            start_date_standardized_datetime = datetime.strptime(dates_processed[0]["date_standardized"], "%Y-%m-%d")
        except ValueError:
            start_date_standardized_datetime = datetime.strptime("1000-01-01", "%Y-%m-%d")
        """
    if end_date_standardized:
        end_date_standardized_datetime = datetime.strptime(end_date_standardized, "%Y-%m-%d")
    else:
        end_date_standardized = None
        end_date_standardized_datetime = None


    # Roman numerals in words
    # There are only a few first letters to be able to correctly identify the associated number but also to be able to take into account possible grammatical declension
    roman_numerals_words = {
        "un": 1, "du": 2, "tr": 3, "quat": 4, "quinque": 5, "sex": 6, "septem": 7, "octo": 8, "novem": 9, "decem": 10,
        "undec": 11, "duodec": 12, "tredec": 13, "quattuordec": 14, "quindec": 15, "sedec": 16, "septendec": 17,
        "duodev": 18, "undev": 19, "viginti": 20
    }

    # Roman numerals extracted
    roman_numerals_extracted = []
    roman_numerals_words_extracted = []

    # Arabic numerals converted
    arabic_numerals_converted_from_latin_numerals = []
    arabic_numerals_converted_from_words = []

    # Counts
    count_roman_numerals_extracted = 0
    count_roman_numerals_words_extracted = 0

    # This variable will only be used for internal calculations.
    start_date_standardized_datetime_recalculated = None

    # Processing
    # ------------------------------------------------------

    # Find matches using regular expressions
    week_one_matches = re.findall(r'\b(' + '|'.join(week_singular) + r')\b', line)
    week_many_matches = re.findall(r'\b(' + '|'.join(week_plural) + r')\b', line)

    # 1. Duration is 1 week
    # ------------------------------------------------------
    # in case there are both mentions of "one week" and "many weeks" we will report error below (duration_uncertainty = 1) take the mention of "one week" (to do it we start with condition "if week_one_matches")
    if week_one_matches:
        if len(week_one_matches) > 1:
            duration_uncertainty = 1
        # Text with extracted duration
        preceding_words_extracted = extract_preceding_words(line, week_one_matches, excerpt_size)
        duration_extracted = "[...] " + ' '.join(preceding_words_extracted + week_one_matches) + " [...]"
        duration_standardized_in_weeks = 1
        duration_standardized_in_days = 7

        # if there are start date known we can calculate the end date
        if start_date_standardized_datetime:
            end_date_standardized_datetime = start_date_standardized_datetime + timedelta(days=7)
            end_date_uncertainty = 1

    # 2. Duration is many weeks
    # ------------------------------------------------------
    elif week_many_matches:
        # report uncertainty if there are few mentions of "many weeks" in the same line(for exemple: "VI septimanarum" and "XI septimanis")
        if len(week_many_matches) > 1:
            duration_uncertainty = 1

        # if many mentions, we will take the first one correspondig the sequence position in the week_plural variable
        preceding_words_extracted = extract_preceding_words(line, week_plural, excerpt_size)


        # 2.1 Determine the number of weeks
        # ------------------------------------------------------
        """
        The number of weeks can be expressed in Roman numerals (for example, "VIII") as well as in words (for example, "octo"). So we must take each word that precedes the word "week" ("septiman...") and analyze it to determine the number of weeks.
        """

        # process each word that precedes the word "week" ("septiman...")
        for word in preceding_words_extracted:

            # determine if this word is Roman numeral
            if extract_roman_numerals(word):
                # the preceding words can contains a several Roman numerals. So we will count theses numerals to report latter uncertainty
                count_roman_numerals_extracted += 1
                # collect all Roman numerals extracted
                roman_numerals_extracted.append(word)
                # convert all extracted Roman numerals to Arabic numerals
                arabic_numerals_converted_from_latin_numerals, conversion_uncertainty = convert_roman_to_arabic(roman_numerals_extracted)

                # we will take the last value (as more closed to target word) and convert it to arabic numerals


            # determine if this word is numeral expressed in word
            # (to do it, we will use a dictionary of numerals expressed in word)
            for roman_word, arabic_numeral in roman_numerals_words.items():
                # we will compare each word from preceding words of mention week to numerals expressed in word
                if word.lower().startswith(roman_word):
                # the preceding words can contains a several Roman numerals. So we will count theses numerals to report latter uncertainty
                    count_roman_numerals_words_extracted += 1
                    roman_numerals_words_extracted.append(word) # not used, just in case, if need to acces this data
                    # collect all numerals extracted and converted from numerals expressed in words
                    arabic_numerals_converted_from_words.append(arabic_numeral)


        # 2.2 Set up duration
        # (duration expressed in weeks & in days and text with extracted duration)
        # --------------------------------------------------------------------------
        """
        If there are numbers expressed both in Roman numerals and in latin letters, we will prioritize the numbers expressed in Roman numerals. (This is why we chose these numbers first.) If there are no numbers expressed in Roman numerals, we will then consider those expressed in letters.
        It's important to note that in all cases, we select the number (whether expressed as numerals or letters) that is closest to the target word. In practice, this means selecting the number that appears last in the list of extracted numbers. Our principle is that the closer the number is to the target word, the greater the likelihood that it exactly the word wich represents the duration we are trying to identify.
        """
        # final - set up the number of weeks as integer number (e.g. duration_standardized_in_weeks = "8")
        if arabic_numerals_converted_from_latin_numerals:
            duration_standardized_in_weeks = arabic_numerals_converted_from_latin_numerals[-1]
        elif arabic_numerals_converted_from_words:
            duration_standardized_in_weeks = arabic_numerals_converted_from_words[-1]

        # if we know the number of weeks, we will convert it to days (i.e. 8 weeks = 8 x 7 = 56 days)
        if duration_standardized_in_weeks:
            duration_standardized_in_days = duration_standardized_in_weeks * 7

        # Text with extracted duration
        duration_extracted = "[...] " + ' '.join(preceding_words_extracted + week_many_matches) + " [...]"



        # 2.3 Report duration uncertainty in case of many weeks
        # --------------------------------------------------------------------------
        # The conditions for reporting duration uncertainty when processing 'plural weeks' is as follows: 
        """
        The decision to separate the conditions into multiple lines was deliberate. We chose this approach because, although it may be more verbose, it is also more understandable, and easier to maintain and manage.
        """

        # if there are more than 1  numerals expressed in latin numerals
        duration_uncertainty = 1 if count_roman_numerals_extracted > 1 else duration_uncertainty
        # if there are more than 1 numerals expressed in latin words
        duration_uncertainty = 1 if count_roman_numerals_words_extracted > 1 else duration_uncertainty
        # report the error if there are also numerals expressed in latin numerals and in the latin words
        duration_uncertainty = 1 if count_roman_numerals_extracted > 0 and count_roman_numerals_words_extracted > 0 else duration_uncertainty
        # report the error if there are no numerals expressed in latin numerals or in the latin words
        duration_uncertainty = 1 if count_roman_numerals_extracted == 0  and count_roman_numerals_words_extracted == 0 else duration_uncertainty
        # if there is a problem during conversation of latin numerals to arabic numerals 
        duration_uncertainty = 1 if conversion_uncertainty > 0 else duration_uncertainty


        # 2.4 Calculate the end date and, if necessary, the new start date
        # --------------------------------------------------------------------------
        # if there are start date and duration we can calculate the end date and recalculate the start date (see explanation)
        if start_date_standardized_datetime and duration_standardized_in_days:
            # calculate end date
            end_date_standardized_datetime = start_date_standardized_datetime + timedelta(days=7)
            end_date_uncertainty = 1

            # calculate new start date
            start_date_standardized_datetime_recalculated = start_date_standardized_datetime - timedelta(days=duration_standardized_in_days - 7)
            start_date_uncertainty = 1



    # 3. Report duration uncertainty for general cases
    # ------------------------------------------------------
    # Conditions to report duration uncertainty for general cases:

    # if there are both mentions of "one week" and "many weeks"
    duration_uncertainty = 1 if week_one_matches and week_many_matches else duration_uncertainty
    # if there are no mentions neither week_one_matches or week_many_matches
    duration_uncertainty = 1 if not week_one_matches and not week_many_matches else duration_uncertainty


    # 4. Convert the dates obtained to string to insert into database
    # -----------------------------------------------------------------

    # if there are date end and a new start date (both as datetime objects) we can convert them to string date
    if end_date_standardized_datetime:
        end_date_standardized = end_date_standardized_datetime.strftime("%Y-%m-%d")
    if start_date_standardized_datetime_recalculated:
        start_date_standardized = start_date_standardized_datetime_recalculated.strftime("%Y-%m-%d")

    """
    Some explanations about multi-weeks sums:
    
    Multi-week sums typically follow multiple one-week sums. When dealing with sums spanning several weeks, determining start and end dates becomes more complex due to the absence of specific dates. To recalculate these dates, we rely on two key pieces of information: the duration in weeks and the supposed start date, which actually corresponds to the last known date—specifically, the start date of the last one-week sum.

    To calculate the end date, we add a week to the supposed start date (the start date of the last one-week sum). For the start date, we subtract one week from the total duration of several weeks (as we've already added one week) and subtract this adjusted duration from the last known start date (the start date of the last one-week sum).

    This explanation must clarifies the process. If not, referring back to the original text may provide further insight into the construction of sums spanning multiple weeks.
    """


    return start_date_standardized, start_date_uncertainty, end_date_standardized, end_date_uncertainty, duration_extracted, duration_standardized_in_days, duration_uncertainty



# =====================================================
# Extract preceding word befor mention of duration
# =====================================================
"""
Description:
This function extract given number of words imediatly preceding target word.

Parameters:
- text (str): The text where you have to find and extract the words.
    >>> Example: text = "Summa summarum IV predictarum septimanarum proxime dictarum est..."
- target_words (list, string): The words that must be found before which we will extract part of the text.
    >>> Example: target_words = ["septimanas", "septimanarum", "septimanis"]
- excerpt_size (int): Number of words in excerpt. 
    >>> Example: excerpt_size = 2

Returns:
- preceding_words (list, str): The list of string of extracted words. It will return all preceding words if excerpt size is larger than available words. And it will return None if no target word is found in the text.
    >>> Example: preceding_words = ['IV', 'predictarum']

"""

# Functions
def extract_preceding_words(line, target_words, excerpt_size):
    excerpt = []
    for target_word in target_words:
        # Find the position of the target word in the text
        match = re.search(r'\b' + re.escape(target_word) + r'\b', line)
        if match:
            # Extract the substring preceding the target word
            preceding_text = line[:match.start()]
            # Split the preceding text into words
            preceding_words = preceding_text.split()
            # Take the excerpt starting from the target word
            if len(preceding_words) >= excerpt_size:
                excerpt = preceding_words[-excerpt_size:]
                return excerpt
            else:
                return preceding_words  # Return all preceding words if excerpt size is larger than available words
    return []  # Return None if no target word is found in the text



