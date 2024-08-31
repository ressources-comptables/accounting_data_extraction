"""
Module: manual_1_new_transactions.py

Description:
Process new line identified as "Transaction" during manual verification after first automatic integration data in database.
This processing identify amounts in these lines.

"""

# Import custom functions
# ------------------------------------------
from database_config import connect_to_database
from main_handler_amount import process_amount


# ==============================
# Processing
# ==============================

# connect to database
# -------------------------
connection = connect_to_database()

# create a cursor object
cursor = connection.cursor(buffered=True)

# execute the query
query = """
SELECT
    l.line_id,
    l.text
FROM
    line l
LEFT JOIN amount_composite ac ON
    l.line_id = ac.line_id
LEFT JOIN amount_simple ams ON
    l.line_id = ams.line_id
WHERE
    ac.line_id IS NULL
    AND ams.line_id IS NULL
    AND l.line_type_id IN (2, 6, 8, 7, 5)
"""
cursor.execute(query)

# fetch the results
results = cursor.fetchall()

# process function
# -------------------------

processed_count = 0
for row in results:
    line_id = row[0]  # type: ignore # l.line_id
    line = row[1]     # type: ignore # l.text
    process_amount(cursor, line, line_id)
    processed_count += 1

# Commit the transaction after processing all rows
connection.commit()

# Print the number of processed rows
print(f"{processed_count} rows were processed")

# close the cursor and connection
cursor.close()
connection.close()


