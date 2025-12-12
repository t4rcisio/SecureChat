import ctypes
import datetime
import os
import sys
import requests

from PyQt6 import QtWidgets, QtGui
import traceback

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QMessageBox, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit

import json
import asyncio
import websockets
from PyQt6.QtCore import QThread, pyqtSignal
from pages import main

VERSION="1.0"
APP_NAME = "SECURE CHAT"
APP_ID = "SECURE-CHAT"
ORGANIZATION = "Sistemas Distribuídos"

DB_TOKEN = 'dev-internal-token'
DB_URL = 'http://127.0.0.1:8000'
CHAT_URL = 'http://127.0.0.1:8000'

USER_DIR = ".\\user"




class WebSocketListener(QThread):
    evento_recebido = pyqtSignal(dict)

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.running = True

    def run(self):
        # ✅ CRIA UM LOOP ASYNC EXCLUSIVO PARA ESSA THREAD
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.listen())

    async def listen(self):
        url = f"ws://127.0.0.1:9100/ws/{self.username}"

        try:
            async with websockets.connect(url) as ws:
                while self.running:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    self.evento_recebido.emit(data)

        except Exception as e:
            print("❌ WebSocket erro:", e)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()



class App:


    def __init__(self):

        os.makedirs(USER_DIR, exist_ok=True)

        self.headers = {
            "x-internal-token": DB_TOKEN,
            "Content-Type": "application/json"
        }

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
        self.current_contact = False

        self.homePage.opne_login_btn.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(2))
        self.homePage.open_new_accont_btn.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(1))

        self.homePage.back.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(0))
        self.homePage.back_2.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(0))
        self.homePage.back_3.clicked.connect(lambda state: self.volta_lista())

        self.homePage.login.clicked.connect(lambda state: self.__login())

        self.homePage.back_4.clicked.connect(lambda state: self.homePage.stackedWidget.setCurrentIndex(3))

        self.homePage.pushButton_5.clicked.connect(lambda state: self.open_user_data())

        self.homePage.pushButton_5.clicked.connect(lambda state: self.open_user_data())

        self.homePage.save.clicked.connect(lambda state: self.__create_account())

        self.homePage.back_5.clicked.connect(lambda state: self.exit())

        self.homePage.search_btn.clicked.connect(lambda state: self.__add_contact())

        self.homePage.send.clicked.connect(lambda state: self.send_message())

        self.homePage.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.homePage.password_2.setEchoMode(QLineEdit.EchoMode.Password)
        self.homePage.password_3.setEchoMode(QLineEdit.EchoMode.Password)
        self.homePage.password_4.setEchoMode(QLineEdit.EchoMode.Password)
        self.homePage.password_5.setEchoMode(QLineEdit.EchoMode.Password)

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

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_contacts_page)

        # Executar a cada 1 minuto (60.000 ms)
        self.timer.start(5_000)

    def exit(self):

        self.user_params = False
        self.current_contact = False
        self.homePage.stackedWidget.setCurrentIndex(0)

    def open_user_data(self):

        self.homePage.stackedWidget.setCurrentIndex(5)

        self.homePage.name_2.setText(self.user_params["name"])
        self.homePage.user_3.setText(self.user_params["username"])
        self.homePage.email_2.setText(self.user_params["email"])



    def volta_lista(self):

        self.current_contact = False
        self.homePage.stackedWidget.setCurrentIndex(3)

    def send_message(self):

        payload = {
            "sender": self.user_params['username'],
            "receiver": self.current_contact["username"],
            "content": self.homePage.message_input.text(),
        }

        resp = requests.post(CHAT_URL + f"/send", json=payload)

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

        self.homePage.scrollArea_2.widget().adjustSize()
        QtWidgets.QApplication.processEvents()

        self.homePage.scrollArea_2.verticalScrollBar().setValue(
            self.homePage.scrollArea_2.verticalScrollBar().maximum()
        )

    def mensagem_recebida(self, data):

        sender = data["sender"]

        #  Se o usuário ainda não existe na lista → cria card novo
        if sender not in self.cards_conversas:

            response = requests.get(f"{DB_URL}/user/{sender}", headers=self.headers)
            if response.status_code == 200:
                response_json = response.json()

                try:
                    card = self.criar_card_conversa(response_json["name"], sender, datetime.datetime.now().isoformat())
                except:
                    return
                self.cards_conversas[sender] = card
                self.nao_lidas[sender] = 0

                card.mousePressEvent = lambda event, id=sender: self.open_contact_chat(id)
                self.scrollLayout_2.insertWidget(0, card)

        self.nao_lidas[sender] += 1

        card = self.cards_conversas[sender]
        card.badge.setText(str(self.nao_lidas[sender]))
        card.badge.show()

        self.__show_conversations()


    def buscar_historico(self, user1, user2):
        url = f"{CHAT_URL}/history/{user1}/{user2}"
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

        #self.homePage.label_13.setText('<html><head/><body><p><span style=" font-size:18pt; font-weight:600; color:#00165e;">'+str(self.current_contact['name'])+'</span></p></body></html>')
        self.homePage.label_13.setText('<html><head/><body><p><span style=" font-size:18pt; font-weight:600; color:#00165e;">'+self.current_contact['name'].upper()+' </span><span style=" font-size:12pt; font-weight:600; color:#00165e;"></br>(@'+self.current_contact['username']+')</span></p></body></html>')
        self.homePage.stackedWidget.setCurrentIndex(4)
        self.__show_history()

    def __add_contact(self):

        user_name = self.homePage.search.text()

        if user_name == self.user_params['username']:
            return

        resp = requests.get(DB_URL + f"/user/{user_name}", headers=self.headers)

        if resp.status_code == 200:

            self.current_contact = resp.json()
            self.open_chat()

        else:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro",
                                 f"O usuário {user_name} não foi encontrado")
            return


    def buscar_conversas(self, username):

        url = f"{CHAT_URL}/conversations/{username}"
        response = requests.get(url)
        return response.json()

    def update_contacts_page(self):

        current_page = self.homePage.stackedWidget.currentIndex()

        if current_page != 3:
            return

        self.__show_conversations()


    def __show_conversations(self):

        self.clear_layout(self.scrollLayout_2)

        if self.user_params == False:
            return

        conversas = self.buscar_conversas(self.user_params['username'])

        for u_id, dt in conversas:

            response = requests.get(f"{DB_URL}/user/{u_id}", headers=self.headers )

            if response.status_code == 200:

                response_json = response.json()

                if 'name' in response_json:

                    card = self.criar_card_conversa(response_json["name"], u_id, dt)
                    self.cards_conversas[u_id] = card
                    card.mousePressEvent = lambda event, id=u_id: self.open_contact_chat(id)
                    self.scrollLayout_2.addWidget(card)

        self.scrollLayout_2.addStretch()

        if self.current_contact != False:

            self.open_contact_chat(self.current_contact["username"])
        else:
            self.homePage.stackedWidget.setCurrentIndex(3)

    def open_contact_chat(self, u_id):

        resp = requests.get(DB_URL + f"/user/{u_id}", headers=self.headers)

        if resp.status_code == 200:

            self.current_contact = resp.json()
            self.open_chat()

            self.nao_lidas[u_id] = 0

            card = self.cards_conversas[u_id]
            card.badge.hide()

        else:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro",
                                 f"O usuário {u_id} não foi encontrado")
            return

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

    def criar_card_conversa(self, nome, u_id, dt_str):
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

        # FOTO / AVATAR
        foto = QLabel()
        pixmap = QPixmap(".\\sources\\profile-circle-svgrepo-com.png")
        foto.setPixmap(
            pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        foto.setFixedSize(40, 40)

        # ✅ NOME + TEMPO
        nome_label = QLabel(
            f'<span style="font-size:10pt; font-weight:600; color:#00165e;">{nome.upper()} </span>'
            f'<span style="font-size:9pt; font-weight:600; color:#00165e;">(@{u_id})</span>'
        )

        nome_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1f2933;")

        d_tme = self.tempo_relativo(dt_str)
        tempo_label = QLabel(d_tme)
        tempo_label.setStyleSheet("font-size: 11px; color: gray;")

        texto_layout = QVBoxLayout()
        texto_layout.addWidget(nome_label)
        texto_layout.addWidget(tempo_label)


        if u_id in self.nao_lidas:
            ct = self.nao_lidas[u_id]
        else:
            ct = 0
            self.nao_lidas[u_id] = 0

        badge = QLabel(str(ct))
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet("""
            QLabel {
                background-color: #22c55e;
                color: white;
                border-radius: 11px;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        if not ct and d_tme != "agora":
            badge.hide()

        if d_tme == "agora" and self.nao_lidas[u_id] == 0:
            self.nao_lidas[u_id] = 1
            badge.setText("1")

        layout.addWidget(foto)
        layout.addLayout(texto_layout)
        layout.addStretch()
        layout.addWidget(badge)


        card.badge = badge
        card.user_id = u_id

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

        try:
            resp = requests.post(DB_URL+"/register", json=payload, headers=self.headers )
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


        for i in payload:
            if len(payload[i].strip()) < 3:
                self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"O campo [{i.upper()}] precisa tem mais de três caracteres")
                return


        try:
            resp = requests.post(DB_URL+"/login", json=payload)
        except:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"Ocorreu um falha ao conectar com o servidor")
            return

        if resp.status_code == 401:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"Usuário ou senha inválidos")
            return

        if resp.status_code != 200:
            self.show_messageBox(QMessageBox.Icon.Warning, "Erro", f"Ocorreu um falha ao conectar com o servidor {resp.content}")
            return


        if resp.status_code == 200:

            if resp.json()["ok"]:

                self.cards_conversas = {}
                self.nao_lidas = {}

                self.user_params = resp.json()
                self.__show_conversations()

                self.ws_listener = WebSocketListener(self.user_params['username'])
                self.ws_listener.evento_recebido.connect(self.mensagem_recebida)
                self.ws_listener.start()

                self.homePage.user_2.setText(""),
                self.homePage.password_3.setText(""),


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