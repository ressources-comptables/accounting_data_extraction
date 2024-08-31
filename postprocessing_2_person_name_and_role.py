"""
Module: postprocessing_2_person_name_and_role.py

Description:
Process persons names and roles before to create the standardized persons names and roles. 
After this, these standardized persons names and roles must me verified and modified if needed.
"""

# Import custom functions
# ------------------------------------------
from database_config import connect_to_database


# =========================================================================
# Function: “Standardization” of person names and extraction of their roles
# =========================================================================

def process_person_name_and_role(cursor):

    # Initialize variables
    participant_name = ""

    # Select distinct values from the "participant_name_extracted" column in the "participant" table
    # -------------------------
    cursor.execute("SELECT DISTINCT participant_name_extracted FROM participant")
    participant_names = cursor.fetchall()

    # Process person name
    # -------------------------

    # Process each participant
    for participant_name_tuple in participant_names:
        participant_name = participant_name_tuple[0] # type: ignore  # Extracting the value from the tuple

        if participant_name: # to exclude null values
            # Check if the participant name doesn't already exist in the "person" table
            cursor.execute("SELECT person_id FROM person WHERE person_name_standardized = %s", (participant_name,)) # type: ignore
            existing_person = cursor.fetchone()

            if not existing_person:
                # Insert the participant name into the "person" table
                cursor.execute("INSERT INTO person (person_name_standardized, person_type_id) VALUES (%s, %s)", (participant_name, 1)) # type: ignore
                #  person_type_id = 1 (natural person)
                person_id = cursor.lastrowid  # Retrieve auto-incremented ID
            else:
                person_id = existing_person[0]  # Get the existing person ID # type: ignore

            # Update the "person_id" column in the "participant" table
            cursor.execute("UPDATE participant SET person_id = %s WHERE participant_name_extracted = %s", (person_id, participant_name)) # type: ignore
            
            # Commit the changes after updating the person_id
            # cursor.connection.commit()


            
            
            # Process person role
            # --------------------------

            # Fetch all unique participant roles for the current participant name
            cursor.execute("SELECT DISTINCT participant_role_extracted FROM participant WHERE participant_name_extracted = %s", (participant_name,)) # type: ignore
            participant_roles = cursor.fetchall()

            # Insert participant roles into the person_role table
            for role_tuple in participant_roles:
                role = role_tuple[0] # type: ignore
                if role:
                    # Check if the role doesn't already exist in the "person_role" table
                    cursor.execute("SELECT person_role_id FROM person_role WHERE person_role_name_standardized = %s", (role,)) # type: ignore
                    existing_role = cursor.fetchone()

                    if not existing_role:
                        # Insert the role into the "person_role" table
                        cursor.execute("INSERT INTO person_role (person_role_name_standardized) VALUES (%s)", (role,)) # type: ignore
                        #  Retrieve auto-incremented ID for the newly inserted role
                        role_id = cursor.lastrowid
                    else:
                        role_id = existing_role[0]  # Get the existing role ID # type: ignore

                    # Insert the participant role into the "person_occupation" table
                    cursor.execute("INSERT INTO person_occupation (person_id, person_role_id) VALUES (%s, %s)", (person_id, role_id)) # type: ignore
            
            # Commit the changes after inserting participant roles
            # cursor.connection.commit()

    print("All people's names and roles have been processed.")



# ==============================
# Processing
# ==============================

# connect to database
connection = connect_to_database()

# create a cursor object
cursor = connection.cursor(buffered=True)

# execute function
process_person_name_and_role(cursor)

# commit the transaction and close database connection
connection.commit()
cursor.close()
connection.close()
