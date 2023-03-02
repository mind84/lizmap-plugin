__copyright__ = 'Copyright 2023, 3Liz'
__license__ = 'GPL version 3'
__email__ = 'info@3liz.org'

import logging
import re

from html import escape, unescape

from qgis.core import QgsApplication, QgsVectorLayer
from qgis.gui import QgsExpressionBuilderDialog
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWebKit import QWebSettings
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox

from lizmap.qgis_plugin_tools.tools.i18n import tr
from lizmap.qgis_plugin_tools.tools.resources import load_ui, resources_path

FORM_CLASS = load_ui('ui_html_editor.ui')

LOGGER = logging.getLogger('Lizmap')

# RegEx defined in QgsExpression.replaceExpressionText
# This function replaces each expression between [% and %] in the string
# with the result of its evaluation with the specified context.
QGIS_EXPRESSION_TEXT = re.compile(r'\[%(.*?)%]', re.MULTILINE | re.DOTALL)


def expression_from_qgis_to_html(match):
    """ Method to escape QGIS expression to be displayed in HTML. """
    if not match:
        return ''
    return escape(match.group())


def expression_from_html_to_qgis(match) -> str:
    """ Method to unescape QGIS expression to be used in QGIS. """
    if not match:
        return ''
    return unescape(match.group())


class HtmlEditorDialog(QDialog, FORM_CLASS):

    def __init__(self, layer: QgsVectorLayer = None):
        # noinspection PyArgumentList
        QDialog.__init__(self)
        self.setupUi(self)

        if layer:
            self.setWindowTitle(tr("HTML tooltip for the layer '{}'").format(layer.name()))

        self.add_field_expression.setText('')
        self.add_field_expression.setIcon(QIcon(QgsApplication.iconPath("symbologyAdd.svg")))
        self.add_field_expression.setToolTip(tr('Add the current expression in the HTML'))

        self.add_expression.setText('')
        self.add_expression.setIcon(QIcon(QgsApplication.iconPath("mActionAddExpression.svg")))
        self.add_expression.setToolTip(tr('Open the expression builder'))

        self.add_field_expression.clicked.connect(self.add_expression_field_in_html)
        self.add_expression.clicked.connect(self.add_expression_in_html)

        accept_button = self.button_box.button(QDialogButtonBox.Ok)
        accept_button.clicked.connect(self.accept)
        cancel_button = self.button_box.button(QDialogButtonBox.Cancel)
        cancel_button.clicked.connect(self.reject)

        with open(resources_path('html', 'html_editor.html'), encoding='utf8') as f:
            html_content = f.read()

        # noinspection PyArgumentList
        base_url = QUrl.fromLocalFile(resources_path('html', 'html_editor.html'))
        self.web_view.setHtml(html_content, base_url)

        self.web_view.settings().setAttribute(QWebSettings.LocalContentCanAccessRemoteUrls, True)
        self.web_view.settings().setAttribute(QWebSettings.LocalContentCanAccessFileUrls, True)
        self.web_view.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
        self.web_view.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)
        self.web_view.settings().setAttribute(QWebSettings.DnsPrefetchEnabled, True)

        if layer:
            index = self.stacked_expression.indexOf(self.page_layer)
            self.field_expression_widget.setLayer(layer)
        else:
            index = self.stacked_expression.indexOf(self.page_no_layer)
        self.stacked_expression.setCurrentIndex(index)

    def html_content(self) -> str:
        """ Returns the content as an HTML string. """
        html_content = self._js('tEditor.getHtml();')
        return QGIS_EXPRESSION_TEXT.sub(expression_from_html_to_qgis, html_content)

    def set_html_content(self, content: str):
        """ Set the HTML in the editor. """
        html_content = QGIS_EXPRESSION_TEXT.sub(expression_from_qgis_to_html, content)
        self._js('tEditor.setHtml(`{}`);'.format(html_content))

    def _insert_text(self, text: str):
        """ Insert text at the current cursor position. """
        LOGGER.debug("Adding expression '{}' in the HTML".format(text))
        self._js('tEditor.insertText(`[% {} %]`);'.format(text))

    def selected_text(self) -> str:
        """ Get Text selected by the user """
        return self._js('tEditor.getSelectedText();')

    def add_expression_field_in_html(self):
        """ To add the pre-defined expression from the widget in the HTML editor. """
        self._insert_text(self.field_expression_widget.expression())

    def add_expression_in_html(self):
        """ Open the expression builder dialog without any layer set. """
        dialog = QgsExpressionBuilderDialog(None)
        if not dialog.exec_():
            return
        self._insert_text(dialog.expressionText())

    def _js(self, command) -> str:
        """ Internal function to execute Javascript in the editor. """
        return self.web_view.page().currentFrame().evaluateJavaScript(command)
