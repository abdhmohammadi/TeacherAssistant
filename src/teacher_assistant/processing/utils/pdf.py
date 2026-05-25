#import pypandoc
#import pymupdf

import re
from PySide6.QtCore import QMarginsF, Qt, QThread, Signal,QObject
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage

from PySide6.QtGui import ( QPageLayout, QPageSize)

from PySide6.QtWidgets import ( QFileDialog, QMessageBox, QLabel,QStackedWidget, QWidget,QPushButton,QVBoxLayout,QMainWindow, QTabWidget)
           
from PySideAbdhUI.Notify import PopupNotifier

class PdfGeneratorApp(QMainWindow):
    
    def __init__(self, data, app_context, parent=None):
        super().__init__(parent)
        self.data = data
        #self.db_config = db_config
        self.app_context = app_context

        self.setWindowTitle("HTML to PDF Generator")
        self.setGeometry(100, 100, 900, 600)

        central = QWidget()
        central.setProperty('class', 'window-background-layer')
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # ---- Loading overlay (stacked on top of content) ----
        self.content_stack = QStackedWidget()
        layout.addWidget(self.content_stack)

        # Page 0: the actual tabbed content
        self.tab_widget = QWidget()
        self.setup_tabs()
        self.content_stack.addWidget(self.tab_widget)

        # Page 1: a simple loading indicator
        loading_widget = QWidget()
        loading_layout = QVBoxLayout(loading_widget)
        loading_label = QLabel("Loading... Please wait.")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_layout.addWidget(loading_label)
        self.content_stack.addWidget(loading_widget)
        self.content_stack.setCurrentIndex(1)   # show loading first

        # ---- Generate PDF button (initially disabled) ----
        self.generate_button = QPushButton("Generate PDF")
        self.generate_button.clicked.connect(self.generate_pdf)
        self.generate_button.setEnabled(False)
        layout.addWidget(self.generate_button)

        # ---- Start the background worker ----
        self.start_worker()

    def setup_tabs(self):
        # Create the tab structure (Quiz + optional Answers).
        layout = QVBoxLayout(self.tab_widget)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Quiz tab
        self.quiz_tab = QWidget()
        quiz_layout = QVBoxLayout()
        self.preview_source = QWebEngineView()
        quiz_layout.addWidget(self.preview_source)
        self.quiz_tab.setLayout(quiz_layout)
        self.tabs.addTab(self.quiz_tab, "Quiz")

        # Answers tab (will be shown only if answer_html not empty)
        self.answers_tab = None
        self.preview_answer = None

    def start_worker(self):
        """Create the worker and connect its signals."""
        self.worker = HtmlGeneratorWorker(self.data, self.app_context)
        self.thread = QThread()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_html_ready)
        self.worker.error.connect(self.on_worker_error)

        # Cleanup
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)#self.thread.deleteLater)

        self.thread.start()

    def on_thread_finished(self):
        del self.thread
        PopupNotifier.Notify(self, message='Operation done!')

    def on_html_ready(self, quiz_html, answer_html):
        # Save HTML for later PDF generation
        self.quiz_html = quiz_html
        self.answer_html = answer_html

        # Update the quiz view
        self.preview_source.setHtml(quiz_html)

        # If there are answers, create the answers tab and load them
        if answer_html:
            self.answers_tab = QWidget()
            answer_layout = QVBoxLayout()
            self.preview_answer = QWebEngineView()
            self.preview_answer.setHtml(answer_html)
            answer_layout.addWidget(self.preview_answer)
            self.answers_tab.setLayout(answer_layout)
            self.tabs.addTab(self.answers_tab, "Answers")

        # Switch from loading screen to the actual content
        self.content_stack.setCurrentIndex(0)
        self.generate_button.setEnabled(True)

    def on_worker_error(self, error_msg):
        """Show error and close the window if loading fails."""
        QMessageBox.critical(self, "Error", f"Failed to load HTML:\n{error_msg}")
        self.close()
    
    def generate_pdf(self):
        
        # Build a combined HTML document from quiz and answer HTML,
        # keeping scripts only in the quiz part, and save as a multi‑page PDF.

        # 1. Remove any <script> blocks from the answer HTML only.
        #    This prevents duplicate declarations and execution‑order issues.
        script_re = re.compile(r'<script\b[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)

        quiz_body = self.quiz_html                    # keep quiz exactly as‑is
        answer_body = script_re.sub('', self.answer_html) if self.answer_html else ''

        # 2. Build the combined HTML – no script manipulation for the quiz.
        combined_html = (
            '<html><head>'
            '<meta charset="utf-8">'
            '<style>@media print { .page-break { page-break-after: always; } }</style>'
            '</head><body>'
            f'<div>{quiz_body}</div>'
        )
        if self.answer_html:
            combined_html += '<div class="page-break"></div>'
            combined_html += f'<div>{answer_body}</div>'

        combined_html += '</body></html>'

        # 3. Create a temporary page for PDF generation
        page = QWebEnginePage()

        def print_to_pdf(finished):
            if not finished:
                QMessageBox.warning(self, "Error", "Failed to load HTML content for PDF.")
                return

            margins = QMarginsF(24, 5, 24, 5)  # left, top, right, bottom in mm
            layout = QPageLayout(
                QPageSize(QPageSize.PageSizeId.A4),
                QPageLayout.Orientation.Portrait,
                margins
            )

            file_name, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)"
            )
            if not file_name:
                return

            page.printToPdf(file_name, layout)

            # Optional notification
            PopupNotifier.Notify(self, 'PDF', f'PDF saved successfully.\n{file_name}')

        # 4. Load the combined HTML and connect the callback
        page.loadFinished.connect(print_to_pdf)
        page.setHtml(combined_html)

class HtmlGeneratorWorker(QObject):
    finished = Signal(str, str)       # quiz_html, answer_html
    error = Signal(str)               # error message

    def __init__(self, data, app_context):
        """
        data        : dict with 'student', 'qb_id', 'quiz-id', 'asign-date', etc.
        db_config   : dict with PostgreSQL connection parameters 
                      (host, port, dbname, user, password)
        app_context : read‑only object with DPI, paths, template config, etc.
        """
        super().__init__()
        self.data = data
        #self.db_config = db_config
        self.app_context = app_context

    def run(self):
        #conn = None
        try:
            # 1. Open a dedicated database connection for this thread
            #conn = psycopg2.connect(**self.db_config)
            #cursor =  conn.cursor()
            cursor = self.app_context.database.connection.cursor()
            # 2. Generate both HTML pieces
            quiz_html = self._generate_quiz_html(cursor)
            answer_html = self._generate_answer_html(cursor)

            # 3. Emit success (both strings)
            self.finished.emit(quiz_html, answer_html)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            if cursor:
                cursor.close()

    # ================================================================
    # HTML generation logic (adapted from your original methods)
    # ================================================================

    def _generate_quiz_html(self, cursor):
        """Generate quiz HTML using the given database cursor."""
        qb_ids = self.data['qb_id']
        if not isinstance(qb_ids, (list, tuple)):
            qb_ids = [qb_ids]

        placeholders = ','.join(['%s'] * len(qb_ids))
        cmd = (
            f'SELECT content_description_, score_ '
            f'FROM educational_resources WHERE id IN ({placeholders})'
        )
        cursor.execute(cmd, qb_ids)
        records = cursor.fetchall()

        if not records:
            return ''

        # Load template
        template_path = self.app_context.resource_path + '\\templates\\01-Quiz-Template.html'
        with open(template_path, encoding='utf-8') as f:
            html = f.read()

        # Row template
        style = 'border-left:none;border-top:none;border-right:none'
        new_row_tmp = (
            '        <tr>\n'
            f'            <td style="{style}; vertical-align:top;">{{0}})</td>\n'
            f'            <td style="{style}; width:{self.app_context.EDU_ITEM_PIXELS}; text-align:{{1}}">{{2}}</td>\n'
            f'            <td style="{style}; vertical-align:top">{{3}}</td>\n'
            '        </tr>\n'
        )

        language = self.app_context.Language
        config = self.app_context.template_config.read()
        text_align = config[language]['Text align']
        total_score = 0.0
        rows = []

        for row, item in enumerate(records):
            total_score += item[1]
            rows.append(new_row_tmp.format(row + 1, text_align, item[0], item[1]))

        html = html.replace('<!-- NEW CONTENT -->', '\n'.join(rows), 1)
        html = self._apply_common_replacements(html, config, language, total_score, mode='quiz')
        return html

    def _generate_answer_html(self, cursor):
        """Generate answer HTML using the given database cursor."""
        quiz_ids = self.data['quiz-id']
        if not isinstance(quiz_ids, (list, tuple)):
            quiz_ids = [quiz_ids]

        placeholders = ','.join(['%s'] * len(quiz_ids))
        cmd = (
            f'SELECT answer_, earned_point_, feedback_ '
            f'FROM quests WHERE id IN ({placeholders})'
        )
        cursor.execute(cmd, quiz_ids)
        records = cursor.fetchall()

        if not records:
            return ''

        template_path = self.app_context.resource_path + '\\templates\\01-Quiz-Template.html'
        with open(template_path, encoding='utf-8') as f:
            html = f.read()

        style = 'border-left:none;border-top:none;border-right:none'
        new_row_tmp = (
            '        <tr>\n'
            f'            <td style="{style}; vertical-align:top;">{{0}})</td>\n'
            f'            <td style="{style}; width:{self.app_context.EDU_ITEM_PIXELS}; text-align:{{1}}">{{2}}</td>\n'
            f'            <td style="{style}; vertical-align:top">{{3}}</td>\n'
            '        </tr>\n'
        )

        feedback_tmp = (
            '        <tr>\n'
            f'           <td style="{style}; vertical-align:top;"></td>\n'
            f'           <td style="{style};color:darkgray; width:{self.app_context.EDU_ITEM_PIXELS}; text-align:{{0}}">{{1}}<br>{{2}}</td>\n'
            f'           <td style="{style}; vertical-align:top;"></td>\n'
            '        </tr>\n'
        )

        language = self.app_context.Language
        config = self.app_context.template_config.read()
        text_align = config[language]['Text align']
        total_score = 0.0
        rows = []

        for row, item in enumerate(records):
            total_score += item[1]
            rows.append(new_row_tmp.format(row + 1, text_align, item[0], item[1]))
            if item[2]:
                label = 'بازخورد:'
                rows.append(feedback_tmp.format(text_align, label, item[2]))

        html = html.replace('<!-- NEW CONTENT -->', '\n'.join(rows), 1)
        html = self._apply_common_replacements(html, config, language, total_score, mode='answer')
        return html

    def _apply_common_replacements(self, html, config, language, total_score, mode):
        """Apply dimension, style, and content placeholders (same as before)."""
        ac = self.app_context
        dimensions = {
            '-- 2.43 inches --': f'{2.43 * ac.DPI}px',
            '-- 2.42 Inches --': f'{2.42 * ac.DPI}px',
            '-- 0.54 Inches --': f'{0.54 * ac.DPI}px',
            '-- 6.19 Inches --': f'{ac.EDU_ITEM_PIXELS}px',
        }
        for old, new in dimensions.items():
            html = html.replace(old, new)

        html = html.replace('-- font-family --', config[language]['Font family'])
        html = html.replace('-- direction --', config[language]['Direction'])
        html = html.replace('-- Text Alignment --', config[language]['Text align'])

        replacements = {
            '-- Stu-Name --': self.data['student'],
            '-- Date --': str(self.data.get('asign-date') or self.data.get('reply-date', '')),
            '-- Book-Grade --': '' if mode == 'quiz' else 'Answer sheet',
            '-- SUM --': str(total_score),
        }
        for placeholder, value in replacements.items():
            html = html.replace(placeholder, value)

        return html
    
