Dataset Installation and Query Log Collection
1. How to Install the Datasets

The paper does not provide a step-by-step installation guide. However, it identifies the DELL DVD Store (DS2) benchmark as its primary dataset. DS2 is a well-known open-source database benchmark suite.

Source

Official Dell DVD Store website

Community mirrors on GitHub

Installation Process
Download

Obtain the DS2 distribution (usually provided as a .tar.gz or .zip file).

Data Generation

The suite includes a Perl script (commonly named Install_DVDStore.pl or ds2_create_data.pl).

Run this script to generate raw CSV data files.

You can specify the dataset size (e.g., Small, Medium, Large).

Database Setup

Use the provided SQL scripts to create the schema in the target RDBMS.

The paper specifically used MySQL.

Data Loading

Import the generated CSV files into the database tables using a bulk loading utility.

Example for MySQL:

LOAD DATA INFILE 'file.csv' INTO TABLE table_name;

2. How to Get the Query Logs

The authors obtained query logs by analyzing how the application interacts with the relational database. In practice, this can be done in two main ways:

MySQL General Query Log

A built-in MySQL feature that records every SQL statement received from clients.

Enable the log:

SET GLOBAL general_log = 'ON';


Log location:

Stored either in a log file (e.g., /var/lib/mysql/hostname.log)

Or in the table mysql.general_log

Application-Level Logging

The Dell DVD Store workload driver (which simulates user activity) often includes its own logging mechanism.

This records the SQL queries sent to the database during execution.

3. Summary of the Authors’ Workflow

The paper follows this experimental workflow:

Generate / Download Data

Used a Perl script to generate MySQL data (illustrated in Figure 3 of the paper).

Analyze

Analyzed the MySQL schema and query logs.

Identified Read Patterns (Step 1 of the proposed technique).

Migrate

Used Apache Sqoop to transfer data from MySQL to HBase after transforming the schema.

https://linux.dell.com/dvdstore/
https://linux.dell.com/dvdstore/readme.txt
https://github.com/fortunewalla/dvdstore

Youtube:
Yarn: https://www.youtube.com/watch?v=KqaPMCMHH4g
sqoop: https://www.youtube.com/watch?v=Lo1MoNKE-l8
DVD-dell:https://www.youtube.com/watch?v=4tHT-5TOrDQ