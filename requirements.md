# Requirements Document

## Introduction

This document specifies requirements for a MySQL data import system designed to efficiently process and load large JSONL files into MySQL database tables. The system handles two data files totaling over 500MB: alias_table.jsonl containing entity alias mappings, and entities.jsonl containing comprehensive entity records with nested data structures.

## Glossary

- **JSONL_Importer**: The system responsible for parsing JSONL files and generating MySQL-compatible SQL scripts
- **JSONL_File**: A text file containing one JSON object per line, where each line is a valid JSON document
- **Alias_Table**: The MySQL table storing alias mappings with columns: id, alias_id, cui, alias
- **Entities_Table**: The MySQL table storing entity records with columns: id, cui, name, aliases, tax_id, definition, organism, types
- **SQL_Script_File**: A text file containing MySQL INSERT statements for data import
- **Import_Report**: A summary document describing the import process results including file counts, row counts, and any errors
- **cui**: Concept Unique Identifier - a string identifier for entities
- **alias_id**: Integer identifier for alias records in the source data

## Requirements

### Requirement 1: Parse JSONL Files

**User Story:** As a database administrator, I want to parse JSONL files into structured data, so that I can import them into MySQL.

#### Acceptance Criteria

1. WHEN a valid JSONL file is provided, THE JSONL_Importer SHALL parse each line as a separate JSON object
2. WHEN an invalid JSON line is encountered, THE JSONL_Importer SHALL log the line number and skip to the next line
3. THE JSONL_Importer SHALL preserve all field values from the source JSON during parsing
4. FOR ALL parsed JSON objects, parsing then serializing then parsing SHALL produce an equivalent object (round-trip property)

### Requirement 2: Create MySQL Table Schemas

**User Story:** As a database administrator, I want MySQL table schemas that match the JSONL file structures, so that the data can be properly stored.

#### Acceptance Criteria

1. THE JSONL_Importer SHALL generate a CREATE TABLE statement for Alias_Table with columns: id (INT AUTO_INCREMENT PRIMARY KEY), alias_id (INT), cui (VARCHAR(50)), alias (TEXT)
2. THE JSONL_Importer SHALL generate a CREATE TABLE statement for Entities_Table with columns: id (INT AUTO_INCREMENT PRIMARY KEY), cui (VARCHAR(50)), name (TEXT), aliases (JSON), tax_id (VARCHAR(50)), definition (TEXT), organism (VARCHAR(255)), types (JSON)
3. THE JSONL_Importer SHALL create an index on the cui column for both Alias_Table and Entities_Table
4. THE JSONL_Importer SHALL set the character encoding to UTF-8 for both tables

### Requirement 3: Generate SQL Insert Scripts

**User Story:** As a database administrator, I want SQL insert scripts split into manageable file sizes, so that I can import large datasets without exceeding system limits.

#### Acceptance Criteria

1. WHEN generating SQL scripts, THE JSONL_Importer SHALL split output files at a maximum size of 50MB
2. THE JSONL_Importer SHALL name SQL script files with a sequential pattern: `{table_name}_part{NNN}.sql`
3. WHEN generating INSERT statements for Alias_Table, THE JSONL_Importer SHALL escape single quotes and special characters in the alias field
4. WHEN generating INSERT statements for Entities_Table, THE JSONL_Importer SHALL convert the aliases and types arrays to MySQL JSON format
5. THE JSONL_Importer SHALL use multi-row INSERT statements with batch sizes of 1000 rows for optimal performance
6. THE JSONL_Importer SHALL write each SQL script file with UTF-8 encoding

### Requirement 4: Handle Large Files Efficiently

**User Story:** As a database administrator, I want the import system to handle large files without memory issues, so that the process completes reliably.

#### Acceptance Criteria

1. WHEN processing JSONL files, THE JSONL_Importer SHALL read files line-by-line without loading the entire file into memory
2. THE JSONL_Importer SHALL process at least 1GB of JSONL data without exceeding 512MB of memory usage
3. WHILE processing large files, THE JSONL_Importer SHALL report progress every 10,000 rows processed
4. THE JSONL_Importer SHALL complete processing of a 300MB JSONL file within 10 minutes on standard hardware

### Requirement 5: Generate Import Report

**User Story:** As a database administrator, I want a report summarizing the import tasks, so that I can verify the data was processed correctly.

#### Acceptance Criteria

1. WHEN import script generation completes, THE JSONL_Importer SHALL generate a report file named `import_report.txt`
2. THE Import_Report SHALL include the total row count for each table
3. THE Import_Report SHALL include the total number of SQL script files generated per table
4. THE Import_Report SHALL include the total size of all SQL script files generated
5. IF any lines were skipped during parsing, THE Import_Report SHALL list the count and line numbers of skipped lines
6. THE Import_Report SHALL include the start time, end time, and total duration of the import process
7. THE Import_Report SHALL list the file paths of all generated SQL scripts

### Requirement 6: Validate Input Data

**User Story:** As a database administrator, I want input data validation, so that I am notified of data quality issues before import.

#### Acceptance Criteria

1. WHEN a JSONL line is missing a required field, THE JSONL_Importer SHALL log a warning with the line number and missing field name
2. THE JSONL_Importer SHALL validate that alias_id contains an integer value for Alias_Table records
3. THE JSONL_Importer SHALL validate that cui contains a non-empty string for both table types
4. THE JSONL_Importer SHALL validate that aliases and types are valid JSON arrays for Entities_Table records
5. THE JSONL_Importer SHALL continue processing after encountering validation warnings without stopping execution

### Requirement 7: Configure Database Connection

**User Story:** As a database administrator, I want to configure the MySQL database connection, so that I can connect to my specific MySQL server instance.

#### Acceptance Criteria

1. THE JSONL_Importer SHALL accept a database host parameter specifying the MySQL server address
2. THE JSONL_Importer SHALL accept a database port parameter specifying the MySQL server port
3. THE JSONL_Importer SHALL accept a database name parameter specifying the target database
4. THE JSONL_Importer SHALL accept a username parameter for authentication
5. THE JSONL_Importer SHALL accept a password parameter for authentication
6. THE JSONL_Importer SHALL support reading connection parameters from a configuration file named `import_config.json`
7. IF connection parameters are not provided, THE JSONL_Importer SHALL use default values: host=localhost, port=3306

### Requirement 8: Execute SQL Scripts Against Database

**User Story:** As a database administrator, I want to execute the generated SQL scripts directly against the MySQL database, so that I can complete the import process without manual steps.

#### Acceptance Criteria

1. WHEN the execute flag is enabled, THE JSONL_Importer SHALL connect to the MySQL database using the configured connection parameters
2. THE JSONL_Importer SHALL execute the CREATE TABLE statements before executing INSERT statements
3. IF a table already exists, THE JSONL_Importer SHALL prompt the user to either skip creation, drop and recreate, or abort the process
4. THE JSONL_Importer SHALL execute SQL script files in sequential order by filename
5. WHEN an SQL error occurs during execution, THE JSONL_Importer SHALL log the error and continue with the next statement
6. THE JSONL_Importer SHALL commit changes after each SQL script file completes successfully
7. THE JSONL_Importer SHALL close the database connection after all scripts have been executed

### Requirement 9: Handle Connection Errors

**User Story:** As a database administrator, I want clear error messages when connection issues occur, so that I can quickly diagnose and fix problems.

#### Acceptance Criteria

1. IF the MySQL server is unreachable, THE JSONL_Importer SHALL display a clear error message with the host and port attempted
2. IF authentication fails, THE JSONL_Importer SHALL display an authentication error without exposing the password
3. IF the target database does not exist, THE JSONL_Importer SHALL offer to create the database or abort
4. IF the connection times out, THE JSONL_Importer SHALL retry the connection up to 3 times with a 5-second delay between attempts
5. WHEN a connection error occurs, THE JSONL_Importer SHALL log the error details to a file named `import_errors.log`
