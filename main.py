import ctypes
import datetime
import os
import sys
import requests

from PyQt6 import QtWidgets, QtGui, QtCore
import traceback

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QLabel, QHBoxLayout

from db_service import update_user
from pages import main

VERSION="1.0"
APP_NAME = "SECURE CHAT"
APP_ID = "SECURE-CHAT"
ORGANIZATION = "Sistemas Distribuídos"

DB_TOKEN = 'dev-internal-token'
DB_URL = 'http://127.0.0.1:8100'

CHAT_URL = 'http://127.0.0.1:9100'

USER_DIR = ".\\user"

class App:


    def __init__(self):

        os.makedirs(USER_DIR, exist_ok=True)

    def initialize(self):

        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)

            self.app = QtWidgets.QApplication(sys.argv)

            # --- Configurações globais ---
            self.app.setApplicationName(APP_NAME)
            self.app.setOrganizationName(ORGANIZATION)
            self.app.setApplicationVersion(str(VERSION))

            # Ícone global (também aparece na barra de tarefas)
            icon_path = '.\\sources\\icon.ico'
            app_icon = QtGui.QIcon(icon_path)
            self.app.setWindowIcon(app_icon)

            # --- Janela principal ---
            self.homePage = main.Ui_Form()
            self.Form = QtWidgets.QWidget()
            self.homePage.setupUi(self.Form)

            self.Form.setWindowIcon(app_icon)
            self.Form.setWindowTitle(f"{APP_NAME} - {ORGANIZATION} - {VERSION}")

            # --- Configuração e inicialização ---
            # self.conf = configure.Configure(self.homePage)
            # self.conf.initPages()

            # Carrega as páginas da aplicação
            self.configure()

            # --- Exibição ---
            self.Form.showMaximized()

            # --- Loop principal ---
            sys.exit(self.app.exec())

        except Exception as e:
            # Captura e exibe traceback em popup
            print(traceback.format_exc())
            self.show_messageBox(QMessageBox.Icon.Critical, "Erro", "Falha ao carregar a aplicação")


    def configure(self):

        self.user_params = False

        self.homePage.opne_login_btn.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(2))
        self.homePage.open_new_accont_btn.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(1))

        self.homePage.back.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(0))
        self.homePage.back_2.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(0))
        self.homePage.back_3.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(3))

        self.homePage.save.clicked.connect(lambda state: self.__create_account())

        self.homePage.login.clicked.connect(lambda state: self.__login())

        self.homePage.search_btn.clicked.connect(lambda state: self.__add_contact())

        self.homePage.send.clicked.connect(lambda state: self.send_message())

        self.scrollWidget = QWidget()
        self.scrollLayout = QVBoxLayout(self.scrollWidget)
        self.scrollLayout.setContentsMargins(0,0,0,0)
        self.scrollLayout.setSpacing(6)
        self.homePage.scrollArea_2.setWidget(self.scrollWidget)
        self.homePage.scrollArea_2.setWidgetResizable(True)

        self.scrollWidget_2 = QWidget()
        self.scrollLayout_2 = QVBoxLayout(self.scrollWidget_2)
        self.scrollLayout_2.setContentsMargins(3, 3, 3, 3)
        self.scrollLayout_2.setSpacing(6)
        self.homePage.scrollArea.setWidget(self.scrollWidget_2)
        self.homePage.scrollArea.setWidgetResizable(True)


    def send_message(self):

        payload = {
            "sender": self.user_params['username'],
            "receiver": self.current_contact["username"],
            "content": self.homePage.message_input.text(),
        }

        resp = requests.post(CHAT_URL + f"/messages/send/", json=payload)

        if resp:
            self.homePage.message_input.setText("")
            self.__show_history()

    def __show_history(self):

        self.clear_layout(self.scrollLayout)

        mensagens = self.buscar_historico(self.user_params['username'], self.current_contact["username"])

        for msg in mensagens:
            enviado = msg["sender"] == self.current_contact["username"]

            balao = self.criar_balao(
                texto=msg["content"],
                datahora=datetime.datetime.fromisoformat(msg["timestamp"]).strftime("%d/%m/%Y %H:%M"),
                enviado=enviado
            )

            self.scrollLayout.addWidget(balao)

        self.scrollLayout.addStretch()

        self.homePage.scrollArea.verticalScrollBar().setValue(
            self.homePage.scrollArea.verticalScrollBar().maximum()
        )

    def buscar_historico(self, user1, user2):
        url = f"{CHAT_URL}/messages/history/{user1}/{user2}"
        response = requests.get(url)
        return response.json()

    def criar_balao(self, texto, datahora, enviado: bool):
        container = QWidget()
        layout = QVBoxLayout(container)

        msg_label = QLabel(texto)
        msg_label.setWordWrap(True)

        if not enviado:
            msg_label.setStyleSheet("""
                background-color: rgb(31, 73, 125);
                color: white;
                padding: 8px;
                border-radius: 10px;
            """)
        else:
            msg_label.setStyleSheet("""
                background-color:  #198c47;
                color: white;
                padding: 8px;
                border-radius: 10px;
            """)

        time_label = QLabel(datahora)
        time_label.setStyleSheet("font-size: 10px; color: gray;")

        layout.addWidget(msg_label)
        layout.addWidget(time_label)

        wrapper = QHBoxLayout()
        if not enviado:
            wrapper.addStretch()
            wrapper.addWidget(container)
        else:
            wrapper.addWidget(container)
            wrapper.addStretch()

        wrapper_widget = QWidget()
        wrapper_widget.setLayout(wrapper)

        return wrapper_widget


    def open_chat(self):

        self.homePage.label_13.setText('<html><head/><body><p><span style=" font-size:18pt; font-weight:600; color:#00165e;">'+str(self.current_contact['name'])+'</span></p></body></html>')
        self.homePage.stackedWidget.setCurrentIndex(4)
        self.__show_history()

    def __add_contact(self):

        user_name = self.homePage.search.text()

        if user_name == self.user_params['username']:
            return

        headers = {
            "x-internal-token": "dev-internal-token",
            "Content-Type": "application/json"
        }

        resp = requests.get(DB_URL + f"/users/{user_name}", headers=headers)

        if resp.status_code == 200:

            self.current_contact = resp.json()
            self.open_chat()

        else:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro",
                                 f"O usuário {user_name} não foi encontrado")
            return


    def buscar_conversas(self, username):

        url = f"{CHAT_URL}/messages/conversations/{username}"
        response = requests.get(url)
        return response.json()

    def __show_conversations(self):

        self.clear_layout(self.scrollLayout)

        conversas = self.buscar_conversas(self.user_params['username'])

        for nome, dt in conversas:
            card = self.criar_card_conversa(nome, dt)
            card.mouseMoveEvent = self.open_audio_file_dialog
            self.scrollLayout_2.addWidget(card)

        self.scrollLayout_2.addStretch()
        self.homePage.stackedWidget.setCurrentIndex(3)

    def open_contact_chat(self, conctac_):

    def tempo_relativo(self, dt_str):
        dt = datetime.datetime.fromisoformat(dt_str)
        delta = datetime.datetime.now() - dt

        segundos = delta.total_seconds()

        if segundos < 60:
            return "agora"
        elif segundos < 3600:
            return f"há {int(segundos // 60)} min"
        elif segundos < 86400:
            return f"há {int(segundos // 3600)} h"
        else:
            return f"há {int(segundos // 86400)} d"

    def criar_card_conversa(self, nome, dt_str):
        card = QWidget()
        card.setFixedHeight(70)

        card.setStyleSheet("""
            QWidget {
                background-color: #f2f2f2;
                border-radius: 12px;
            }
            QWidget:hover {
                background-color: #e4e4e4;
            }
        """)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)

        # ✅ FOTO / AVATAR
        foto = QLabel()
        pixmap = QPixmap(".\\sources\\profile-circle-svgrepo-com.png")  # sua imagem padrão
        foto.setPixmap(
            pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        foto.setFixedSize(40, 40)

        # ✅ NOME + TEMPO
        nome_label = QLabel(nome.upper())
        nome_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2933;")

        tempo_label = QLabel(self.tempo_relativo(dt_str))
        tempo_label.setStyleSheet("font-size: 11px; color: gray;")

        texto_layout = QVBoxLayout()
        texto_layout.addWidget(nome_label)
        texto_layout.addWidget(tempo_label)

        layout.addWidget(foto)
        layout.addLayout(texto_layout)
        layout.addStretch()

        return card

    def __create_account(self):

        payload = {
              "name": self.homePage.name.text(),
              "username": self.homePage.user.text(),
              "email": self.homePage.email.text(),
              "password": self.homePage.password.text()
            }

        for i in payload:
            if len(payload[i].strip()) < 3:
                self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"O campo [{i.upper()}] precisa tem mais de três caracteres")
                return


        if self.homePage.password.text() != self.homePage.password_2.text():
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro",f"As senhas não são iguais")
            return

        headers = {
            "x-internal-token": "dev-internal-token",
            "Content-Type": "application/json"
        }

        try:
            resp = requests.post(DB_URL+"/users/create", json=payload, headers=headers)
        except:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"Ocorreu um falha ao conectar com o servidor")
            return

        if resp.status_code != 200:

            if resp.status_code == 400:
                data = resp.json()["detail"]
                self.show_messageBox(QMessageBox.Icon.Warning, "AVISO",
                                     f"{data}")
                return

            self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"Ocorreu um falha ao conectar com o servidor {resp.content}")
            return


        if resp.status_code == 200:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro",
                                 f"Usuário criado com sucesso!")

            self.homePage.stackedWidget.setCurrentIndex(2)

    def __login(self):

        payload = {
            "username": self.homePage.user_2.text(),
            "password": self.homePage.password_3.text(),
        }

        headers = {
            "x-internal-token": "dev-internal-token",
            "Content-Type": "application/json"
        }

        for i in payload:
            if len(payload[i].strip()) < 3:
                self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"O campo [{i.upper()}] precisa tem mais de três caracteres")
                return


        try:
            resp = requests.post(DB_URL+"/users/validate", json=payload, headers=headers)
        except:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"Ocorreu um falha ao conectar com o servidor")
            return

        if resp.status_code != 200:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"Ocorreu um falha ao conectar com o servidor {resp.content}")
            return


        if resp.status_code == 200:

            if resp.json()["ok"]:

                self.user_params = resp.json()
                self.__show_conversations()

            else:
                self.show_messageBox(QMessageBox.Icon.Warning, "Erro",
                                     f"Usuário ou senha incorretos")
                return


    def clear_layout(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                if item.layout() is not None:
                    self.clear_layout(item.layout())

    def show_messageBox(self, type, title, message):

            msg = QMessageBox(self.homePage.widget)
            msg.setIcon(type)
            msg.setWindowTitle(title)
            msg.setText(message)

            msg.setStyleSheet("""
                   QMessageBox { background-color: white; }
                   QMessageBox QLabel { color: rgb(31,73,125); font-weight: bold; }
                   QMessageBox QPushButton {
                       background-color: rgb(31,73,125);
                       color: white;
                       border-radius: 5px;
                       padding: 5px 15px;
                   }
                   QMessageBox QPushButton:hover {
                       background-color: rgb(18,115,176);
                   }
               """)

            msg.exec()

if __name__ == "__main__":
    from multiprocessing import set_start_method

    set_start_method("spawn")
    app = App()
    app.initialize()