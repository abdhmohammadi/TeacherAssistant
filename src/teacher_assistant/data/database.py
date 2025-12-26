from psycopg2 import connect
from psycopg2.extras import execute_values

import datetime
import os
import subprocess
import sys
from psycopg2 import Error
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, connection


class psycopg2_database:

    def __init__(self):
        super().__init__()

    def connect(self,host='', port='', database= '', user='', password=''):
        self.connection = connect(host=host, port=port, database= database, user=user, password=password)
        self.connection.autocommit = False    
  
    def execute(self, query, params=None):
        # Executes INSERT / UPDATE / DELETE
        self.connection.cursor().execute(query, params)
        self.connection.commit()

    def fetchone(self, query, params=None):
        with self.connection.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

    def fetchall(self, query, params=None):
        with self.connection.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    
    def stream(self, query, params=None):
        
        # Returns a cursor that stays open for fetchmany()
        # Caller is responsible for closing it.
        
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        return cursor

    def close(self): self.connection.close()

   
    def get_columns(self, table_name):
        """ Fetch column names from the PostgreSQL table. """
        try:
            
            query = f"""SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}'ORDER BY ordinal_position;"""
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                columns = [row[0] for row in cursor.fetchall()]
                return columns
    
        except Exception as e:
            print("Error fetching table columns:", e)
            return []
    
    
    def bulk_insert_csv(self, data, table_name, column_mapping):
        """Optimized bulk insert with better memory usage and error handling."""
        try:
            # Load CSV in chunks for large files
            total_rows = 0
            
            #import pandas as pd
            for chunk in data:
                # Validate columns
                missing_columns = set(column_mapping.keys()) - set(chunk.columns)
                if missing_columns:
                    raise ValueError(f"Missing columns in CSV: {missing_columns}")
                
                # Reorder and select only needed columns
                chunk = chunk[list(column_mapping.keys())]

                # Convert numpy types to Python native types and handle NaN
                rows = []
                for _, row in chunk.iterrows():
                    processed_row = []
                    for col in column_mapping.keys():
                        value = row[col]
                        # Handle NaN/None
                        if not value:# pd.isna(value):
                            processed_row.append(None)
                        # Convert numpy types
                        elif isinstance(value,):# (numpy.integer,numpy.floating)):
                            processed_row.append(value.item())
                        else:
                            processed_row.append(value)

                    rows.append(tuple(processed_row))
                
                # Construct SQL with original column mapping
                sql_columns = ', '.join(column_mapping.values())
                sql = f"INSERT INTO {table_name} ({sql_columns}) VALUES %s"
                
                # Execute batch insert
                with self.connection.cursor() as cursor:
                    execute_values(cursor, sql, rows, page_size=1000)
                    total_rows += len(rows)
                    print(f"Inserted {len(rows)} rows...")
            
            print(f"Successfully inserted {total_rows} total rows into {table_name}")
            return total_rows
            
        except Exception as e:
            print(f"Error inserting data into {table_name}: {e}")
            return 0


def create_database(connection:connection, database: str):
    """
    Create a new PostgreSQL database
    
    Args:
        db_name: Name of the database to create
        host: Database server host
        port: Database server port
        user: Username for authentication
        password: Password for authentication
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    try:
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        
        # Create a cursor object
        cursor = connection.cursor()
        
        # Check if database already exists
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{database}'")
        exists = cursor.fetchone()
        
        if not exists:
            # SQL query to create a new database
            create_db_query = f'CREATE DATABASE "{database}";'
            
            # Execute the query
            cursor.execute(create_db_query)
            
            connection.commit()

            return True, f"Database '{database}' created successfully"
        else:
            return False, f"Database '{database}' already exists"

    except (Exception, Error) as error:
        return False, f"Error while creating PostgreSQL database: {error}"


def initialize_database(connection:connection):
    """
    Initialize database with tables and initial data
    
    Args:
        db_name: Name of the database to initialize
        host: Database server host
        port: Database server port
        user: Username for authentication
        password: Password for authentication
    """
    
    try:
        
        # Create a cursor object
        cursor = connection.cursor()
        
        # Create tables
        create_tables_query = """
        -- Table: public.academic_years
        -- DROP TABLE IF EXISTS public.academic_years;

        CREATE TABLE IF NOT EXISTS public.academic_years
        (
            id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 100 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 ),
            year_ smallint NOT NULL,
            manager_id text COLLATE pg_catalog."default",
            more_info_ text COLLATE pg_catalog."default",
            CONSTRAINT academic_years_pkey PRIMARY KEY (id)
            USING INDEX TABLESPACE "SCHOOLS"
        );


        ALTER TABLE IF EXISTS public.academic_years
            OWNER to postgres;

        -- Table: public.classroom_events
        -- DROP TABLE IF EXISTS public.classroom_events;

        CREATE TABLE IF NOT EXISTS public.classroom_events
        (
            meeting_no_ smallint NOT NULL,
            pages_start_ smallint NOT NULL,
            pages_end_ smallint NOT NULL,
            subject_ text COLLATE pg_catalog."default" NOT NULL,
            description_ text COLLATE pg_catalog."default" NOT NULL,
            events_ text COLLATE pg_catalog."default",
            analysis_ text COLLATE pg_catalog."default",
            date_time_ timestamp without time zone NOT NULL,
            group_id smallint
        );

        ALTER TABLE IF EXISTS public.classroom_events
            OWNER to postgres;

       -- Table: public.educational_resources
        -- DROP TABLE IF EXISTS public.educational_resources;

        CREATE TABLE IF NOT EXISTS public.educational_resources
        (
            id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 100 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 ),
            source_ text COLLATE pg_catalog."default" NOT NULL,
            content_description_ text COLLATE pg_catalog."default" NOT NULL,
            additional_details_ text COLLATE pg_catalog."default",
            answer_ text COLLATE pg_catalog."default",
            score_ real,
            CONSTRAINT educational_resources_pkey PRIMARY KEY (id)
                USING INDEX TABLESPACE "SCHOOLS"
        );

        ALTER TABLE IF EXISTS public.educational_resources
            OWNER to postgres;
        
        COMMENT ON COLUMN public.educational_resources.source_
            IS 'Stores the address of the text content.';

        COMMENT ON COLUMN public.educational_resources.content_description_
            IS 'Stores the text content of a educational resource or any learning content from high school textbooks.';

        COMMENT ON COLUMN public.educational_resources.additional_details_
            IS 'Additional explanations about the content.';

        COMMENT ON COLUMN public.educational_resources.answer_
            IS 'Stores the answer of the content provided by the teacher.';
        
        -- Table: public.groups
        -- DROP TABLE IF EXISTS public.groups;

        CREATE TABLE IF NOT EXISTS public.groups
        (
            id smallint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 100 MINVALUE 1 MAXVALUE 32767 CACHE 1 ),
            grade_ smallint,
            book_ text COLLATE pg_catalog."default",
            title_ text COLLATE pg_catalog."default",
            events_ text COLLATE pg_catalog."default",
            members_ text COLLATE pg_catalog."default",
            description_ text COLLATE pg_catalog."default",
            CONSTRAINT groups_pkey PRIMARY KEY (id)
                USING INDEX TABLESPACE "SCHOOLS"
        );

        ALTER TABLE IF EXISTS public.groups
            OWNER to postgres;
        
        -- Table: public.observed_behaviours
        -- DROP TABLE IF EXISTS public.observed_behaviours;

        CREATE TABLE IF NOT EXISTS public.observed_behaviours
        (
            id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 100 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 ),
            date_time_ timestamp without time zone NOT NULL,
            student_id text COLLATE pg_catalog."default" NOT NULL,
            observed_behaviour_ text COLLATE pg_catalog."default" NOT NULL,
            analysis_ text COLLATE pg_catalog."default"
        );

        ALTER TABLE IF EXISTS public.observed_behaviours
            OWNER to postgres;

        -- Table: public.personal_info
        -- DROP TABLE IF EXISTS public.personal_info;

        CREATE TABLE IF NOT EXISTS public.personal_info
        (
            id text COLLATE pg_catalog."default" NOT NULL,
            fname_ text COLLATE pg_catalog."default",
            lname_ text COLLATE pg_catalog."default",
            photo_ bytea,
            phone_ text COLLATE pg_catalog."default",
            address_ text COLLATE pg_catalog."default",
            parent_name_ text COLLATE pg_catalog."default",
            parent_phone_ text COLLATE pg_catalog."default",
            additional_details_ text COLLATE pg_catalog."default",
            gender_ text COLLATE pg_catalog."default",
            birth_date_ date,
            CONSTRAINT personal_info_pkey PRIMARY KEY (id)
                USING INDEX TABLESPACE "SCHOOLS"
        );
        
        ALTER TABLE IF EXISTS public.personal_info
            OWNER to postgres;

        -- Table: public.quests
        -- DROP TABLE IF EXISTS public.quests;

        CREATE TABLE IF NOT EXISTS public.quests
        (
            qb_id bigint NOT NULL,
            student_id text COLLATE pg_catalog."default" NOT NULL,
            max_point_ real NOT NULL,
            earned_point_ real NOT NULL DEFAULT 0,
            date_ timestamp without time zone NOT NULL,
            dedline_ timestamp without time zone NOT NULL,
            answer_ bytea,
            reply_date_ timestamp without time zone,
            feedback_ bytea
        );

        ALTER TABLE IF EXISTS public.quests
            OWNER to postgres;
        
        """
        
        # Execute the query
        cursor.execute(create_tables_query)
        
        # Add indexes for better performance
        #index_queries = """
        #CREATE INDEX IF NOT EXISTS idx_edu_source ON educational_resources(source_);
        #CREATE INDEX IF NOT EXISTS idx_edu_score ON educational_resources(score_);
        #CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(setting_key);
        #"""
        #cursor.execute(index_queries)
        
        # Commit the changes
        connection.commit()

        return True, f"Database initialized successfully"
        
    except (Exception, Error) as error:
        return False, f"Error while creating PostgreSQL database: {error}"

def change_database_in_session(connection:connection, database: str,password) -> bool:
    """
    Change database within an existing connection
    Note: In PostgreSQL, you cannot switch databases within a connection.
    This function will close the current connection and create a new one.
    
    Args:
        connection: Existing database connection
        new_db_name: Name of the database to switch to
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get current connection parameters
        params = connection.get_dsn_parameters()
        
        # Close the current connection
        if connection: connection.close()
        
        # Create new connection to the target database
        connection = connect(host=params['host'], port=params['port'], 
                                      user=params['user'], password= password, 
                                      database= database)
        
        return True, connection, f"Successfully switched to database '{database}'"
        
    except (Exception, Error) as error: return False, None, f"Error while changing database: {error}"


def backup_postgres_db(dbname, user, password, host, port, backup_path, dump_path='C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe'):
    
    env = os.environ.copy()
    
    env['PGPASSWORD'] = password
    print(env['PGPASSWORD'])

    # Use full path to pg_dump.exe
    cmd = [
        dump_path,  # ← Fixed path here
        '-Fc', '-v',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-f', backup_path,
        dbname
    ]

    print(f"📦 [{datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}] Starting backup for database '{dbname}' to '{backup_path}'...")

    try:
        # Start process with real-time output streaming
        process = subprocess.Popen(cmd, env=env, stderr=subprocess.PIPE, text=True)

        # Stream stderr output line by line
        while True:
            line = process.stderr.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue
            sys.stdout.write(f"⏳ {line}")
            sys.stdout.flush()

        # Verify completion
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, cmd, stderr=process.stderr.read())

        # Final verification
        if not os.path.exists(backup_path):
            return False, f"❌ Backup failed: File not created", None
        
        if os.path.getsize(backup_path) == 0:
            os.remove(backup_path)
            return False, "❌ Backup failed: Empty file", None
        
        msg = f'✅ [{datetime.datetime.now().strftime("%Y-%m-%d-%H:%M:%S")}] Backup successful.'
        
        print(msg)

        return True, msg, backup_path

    except subprocess.CalledProcessError as e:
        
        error = e.stderr.decode().strip() if e.stderr else str(e)
        
        if os.path.exists(backup_path):
            try: os.remove(backup_path)
            except Exception as e:

                return False, f'Can not remove failed backup history, Error: {e}.', None 
                
        
        return False, f"❌ Backup failed: {error}", None

    except Exception as e:
        return False, f"❌ Unexpected error: {str(e)}", None


def restore_postgres_db(backup_dump_file, target_db, user, password, host, port, overwrite=False, pg_bin_path=r"C:\\Program Files\\PostgreSQL\\17\\bin"):
    
    pg_restore_path = os.path.join(pg_bin_path, "pg_restore.exe")
    createdb_path = os.path.join(pg_bin_path, "createdb.exe")
    dropdb_path = os.path.join(pg_bin_path, "dropdb.exe")

    env = os.environ.copy()
    env['PGPASSWORD'] = password

    # Drop the database if overwrite is True
    if overwrite:
        print(f"⚠️ Dropping existing database '{target_db}'...")
        drop_cmd = [
            dropdb_path,
            '-h', host,
            '-p', str(port),
            '-U', user,
            target_db
        ]
        subprocess.run(drop_cmd, env=env, check=False)

    # Create the database
    print(f"📘 Creating new database '{target_db}'...")
    create_cmd = [
        createdb_path,
        '-h', host,
        '-p', str(port),
        '-U', user,
        target_db
    ]
    try:
        subprocess.run(create_cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        return False, f"❌ Could not create database: {e}", target_db

    # Restore the database from the dump
    print(f"📥 Restoring dump '{backup_dump_file}' into '{target_db}'...")
    restore_cmd = [
        pg_restore_path,
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', target_db,
        '-v',
        backup_dump_file
    ]
    
    try:
        process = subprocess.Popen(restore_cmd, env=env, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

        while True:
            out_line = process.stdout.readline()
            err_line = process.stderr.readline()
            if not out_line and not err_line and process.poll() is not None:
                break
            if out_line:
                sys.stdout.write(f"📄 {out_line}")
            if err_line:
                sys.stderr.write(f"⚠️ {err_line}")

        if process.returncode != 0:
            return False, f"❌ Restore failed with return code {process.returncode}", backup_dump_file

        print(f"✅ [{datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}] Restore completed successfully.")
        return True, "✅ Restore successful.", target_db

    except Exception as e:
        return False, f"❌ Unexpected error during restore: {e}", backup_dump_file

def find_postgresql_bin():
    """
    Locate the PostgreSQL bin folder on a Windows system.
    Returns:
        str: Path to the PostgreSQL bin folder if found, else None.
    """
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")

    possible_paths = [
        os.path.join(program_files, "PostgreSQL"),
        os.path.join(program_files_x86, "PostgreSQL")
    ]

    for base_path in possible_paths:
        if os.path.exists(base_path):
            for version in os.listdir(base_path):
                version_path = os.path.join(base_path, version, "bin")
                if os.path.exists(version_path):
                    return version_path

    return None
