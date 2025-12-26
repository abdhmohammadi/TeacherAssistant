
import time
from PySide6.QtCore import Signal, QObject, QRunnable, Slot

from core.app_context import app_context

# Signals class for thread-safe communication between worker thread and main UI thread
# This allows the background worker to emit events that the main thread can listen to
class DataLoaderSignals(QObject):
    batch_ready = Signal(list)      # Emit batch of records - emitted when a batch of data is ready for UI update
    finished = Signal(int)          # Total loaded count - emitted when loading is complete with total count
    error = Signal(str)             # Message on error - emitted when an error occurs during loading

# Worker class that runs in a background thread to load data from database
# Inherits from QRunnable to enable execution in Qt's thread pool
class DataLoaderWorker(QRunnable):

    def __init__(self, query:str=None, page=0, page_size=50):
        """
        Initialize the data loader worker.
        
        Args:
            query (str, optional): SQL query string to execute. Defaults to None.
            page (int): Page number for pagination (0-indexed). Defaults to 0.
            page_size (int): Number of records per page. Defaults to 50.
        """
        super().__init__()
        
        self.query = query
        self.page = page
        self.page_size = page_size

        # Create signals instance for thread-safe communication
        self.signals = DataLoaderSignals()
        
        # Flag to control worker execution (allows cancellation)
        self.is_running = True

    @Slot()
    def run(self):
        """
        Main execution method that runs in the background thread.
        Executes the query, fetches data in batches, and emits signals for UI updates.
        """
        cursor = None
        try:
            # Build pagination clause for SQL query
            # LIMIT restricts the number of rows, OFFSET skips rows for pagination
            pagination = f"LIMIT {self.page_size} OFFSET {self.page*self.page_size}"

            # Combine the original query with pagination
            full_query = f"{self.query} {pagination}"
            
            # Execute query and get a cursor for streaming results
            cursor = app_context.database.stream(full_query)
            
            # Track total number of records loaded
            total_loaded = 0
            
            # Main loop: fetch data in small batches until done or cancelled
            while self.is_running:
                # Fetch a small batch of rows (20 at a time) for internal processing
                # This prevents loading all data at once and keeps UI responsive
                rows = cursor.fetchmany(20)  # Small internal batches
        
                # If no more rows, exit the loop
                if not rows: break

                # Emit signal to main thread with the batch of data
                # This allows the UI to update incrementally as data loads
                self.signals.batch_ready.emit(rows)
                total_loaded += len(rows)

                # Small sleep to yield control, allowing:
                # - Thread cancellation to be checked
                # - UI thread to process events and stay responsive
                time.sleep(0.005)  # Tiny yield

            # Emit finished signal with total count when loading completes
            self.signals.finished.emit(total_loaded)

        except Exception as e:
            # If any error occurs, emit error signal with error message
            # This allows the UI to display error information to the user
            self.signals.error.emit(str(e))
            
        finally:
            # Cleanup: mark worker as stopped
            self.is_running = False

            # Close database cursor to free resources
            if cursor: cursor.close()

    def stop(self):
        """
        Stop the worker execution.
        Sets the is_running flag to False, which will cause the run() loop to exit.
        """
        self.is_running = False
