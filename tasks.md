# Implementation Plan: JSONL to MySQL Import System

## Overview

A Python-based system to import large JSONL files into MySQL database tables. The implementation follows a streaming architecture to handle large files efficiently, generates SQL scripts with automatic file splitting, and optionally executes them directly against the database.

## Tasks

- [ ] 1. Set up project structure and configuration handling
  - [ ] 1.1 Create project directory structure and configuration module
    - Create src/ directory with empty __init__.py
    - Implement config.py with Config dataclass for database, files, and processing settings
    - Implement load_config() to read from import_config.json with CLI override support
    - Implement CLI argument parsing in main.py skeleton
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

- [ ] 2. Implement JSONL parser with streaming and validation
  - [ ] 2.1 Create JSONLParser class with streaming parse_file method
    - Implement parse_file() yielding (line_number, parsed_dict) tuples
    - Read files line-by-line without loading entire file into memory
    - Use UTF-8 encoding for file reading
    - _Requirements: 1.1, 4.1, 4.2_

  - [ ]* 2.2 Write property test for JSON round-trip consistency
    - **Property 1: JSON Round-Trip**
    - **Validates: Requirements 1.3, 1.4**

  - [ ] 2.3 Implement JSON error handling and logging
    - Catch json.JSONDecodeError and log line number
    - Skip invalid lines and continue processing
    - Track skipped line numbers for reporting
    - _Requirements: 1.2_

  - [ ] 2.4 Implement field validation for both table types
    - Validate alias_id is an integer for alias records
    - Validate cui is a non-empty string for both types
    - Validate aliases and types are valid JSON arrays for entity records
    - Log warnings for missing/invalid fields with line numbers
    - Continue processing after validation warnings
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 3. Implement SQL generator with file splitting
  - [ ] 3.1 Create SQLGenerator class with schema generation
    - Implement generate_schema() for alias_table CREATE TABLE statement
    - Implement generate_schema() for entities_table CREATE TABLE statement
    - Include proper indexes on cui columns
    - Set UTF-8 character encoding (utf8mb4)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 3.2 Implement string escaping and JSON conversion
    - Implement escape_string() to handle single quotes and backslashes
    - Implement to_json_string() to convert Python lists to MySQL JSON format
    - _Requirements: 3.3, 3.4_

  - [ ]* 3.3 Write property test for SQL string escaping
    - **Property 3: SQL String Escaping**
    - **Validates: Requirements 3.3, 3.4**

  - [ ] 3.4 Implement multi-row INSERT generation with file splitting
    - Generate multi-row INSERT statements with batch size of 1000
    - Track current file size and split at 50MB limit
    - Name files with sequential pattern: {table_name}_part{NNN}.sql
    - Write files with UTF-8 encoding
    - _Requirements: 3.1, 3.2, 3.5, 3.6_

  - [ ]* 3.5 Write property test for SQL file size limit
    - **Property 2: SQL File Size Limit**
    - **Validates: Requirements 3.1**

- [ ] 4. Checkpoint - Verify parser and SQL generation
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement database executor with connection handling
  - [ ] 5.1 Create DatabaseExecutor class with connection management
    - Implement __init__ to store connection parameters
    - Implement connect() with retry logic (3 attempts, 5s delay)
    - Implement connection timeout handling
    - _Requirements: 8.1, 9.4_

  - [ ] 5.2 Implement connection error handling and logging
    - Display clear error for unreachable server with host/port
    - Display authentication error without exposing password
    - Offer to create database if it does not exist
    - Log connection errors to import_errors.log
    - _Requirements: 9.1, 9.2, 9.3, 9.5_

  - [ ] 5.3 Implement schema and script execution methods
    - Implement execute_schema() for CREATE TABLE statements
    - Handle existing table prompt (skip/drop-recreate/abort)
    - Implement execute_script() to run SQL script files
    - Execute scripts in sequential order by filename
    - Log SQL errors and continue with next statement
    - Commit after each script file completes
    - Close connection after all scripts execute
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [ ] 6. Implement report generator
  - [ ] 6.1 Create ReportGenerator class with report generation
    - Track and report total row counts per table
    - Track and report SQL script file counts per table
    - Track and report total size of all SQL files
    - List skipped lines with counts and line numbers
    - Include start time, end time, and duration
    - List file paths of all generated SQL scripts
    - Write report to import_report.txt
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_

  - [ ]* 6.2 Write property test for report accuracy
    - **Property 4: Report Accuracy**
    - **Validates: Requirements 5.2, 5.3, 5.4, 5.5**

- [ ] 7. Implement CLI entry point and progress reporting
  - [ ] 7.1 Complete main.py with full workflow orchestration
    - Wire all components together in main() function
    - Implement --execute flag for database execution
    - Implement progress reporting every 10,000 rows
    - Support both config file and CLI argument modes
    - _Requirements: 4.3, 7.6, 8.1_

  - [ ]* 7.2 Write integration tests for end-to-end workflow
    - Test SQL generation without database execution
    - Test full workflow with test database
    - Verify report generation accuracy
    - _Requirements: 1.1, 3.1, 5.1_

- [ ] 8. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design
- Unit tests validate specific examples and edge cases
- The design specifies Python 3.8+ with mysql-connector-python driver

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.3", "2.4", "3.2", "3.4"] },
    { "id": 3, "tasks": ["2.2", "3.3", "3.5", "5.1"] },
    { "id": 4, "tasks": ["5.2", "5.3", "6.1"] },
    { "id": 5, "tasks": ["6.2", "7.1"] },
    { "id": 6, "tasks": ["7.2"] }
  ]
}
```
