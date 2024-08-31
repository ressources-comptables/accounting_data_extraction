# Import libraries
# ------------------------------------------
import mysql.connector # connect to mysql database

# Connect to the database
# ------------------------------------------
def connect_to_database():
    connection = mysql.connector.connect(
        host='your_host',
        port='your_port',
        user='your_username',
        password='your_password',
        database='your_database'
    )
    return connection
