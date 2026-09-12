# UL Test | WissTek-IoT
# 12/09/2026


# ==============================================================================
#  Bibliotecas
# ==============================================================================

import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import serial
import serial.tools.list_ports

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


# ==============================================================================
#  Protocolo
# ==============================================================================

BAUDRATE = 115200
TAMANHO_PACOTE = 20

# Bytes que o firmware sempre deixa zerados - usados para sincronizar o stream
BYTES_ZERADOS = (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17)


def frame_valido(buf, i):
    """Verifica se ha um pacote de UL plausivel comecando em buf[i]."""
    if buf[i] != buf[i + 2]:      # RSSI e gravada em duplicata (bytes 0 e 2)
        return False
    for k in BYTES_ZERADOS:
        if buf[i + k] != 0:
            return False
    return True


def decodifica_rssi(valor_byte):
    """Inverte a conversao de RSSI feita pelo gateway (float dBm -> 1 byte)."""
    if valor_byte <= 127:
        return valor_byte / 2.0 - 74.0
    return (valor_byte - 256) / 2.0 - 74.0


def decodifica_pacote(p):
    """Retorna (luminosidade, rssi_dbm) a partir dos 20 bytes."""
    luminosidade = (p[18] << 8) | p[19]
    rssi = decodifica_rssi(p[0])
    return luminosidade, rssi


# ==============================================================================
#  Leitura serial
# ==============================================================================

class LeitorSerial(threading.Thread):
    """Le a porta serial, sincroniza o stream e entrega pacotes decodificados."""

    def __init__(self, porta, fila_saida):
        super().__init__(daemon=True)
        self.porta = porta
        self.fila = fila_saida
        self._parar = threading.Event()
        self._buf = bytearray()
        self._sincronizado = False

    def parar(self):
        self._parar.set()

    def run(self):
        try:
            ser = serial.Serial(self.porta, BAUDRATE, timeout=0.2)
        except serial.SerialException as exc:
            self.fila.put(("erro", f"Não foi possivel abrir {self.porta}:\n{exc}"))
            return

        self.fila.put(("status", f"Conectado à {self.porta} @ {BAUDRATE} bps"))
        try:
            ser.reset_input_buffer()
            while not self._parar.is_set():
                try:
                    dados = ser.read(max(1, ser.in_waiting))
                except serial.SerialException as exc:
                    self.fila.put(("erro", f"Falha na leitura da serial:\n{exc}"))
                    break
                if dados:
                    self._buf.extend(dados)
                    for pacote in self._extrai_pacotes():
                        self.fila.put(("pacote", decodifica_pacote(pacote)))
                # Protecao contra acumulo de lixo se nunca sincronizar
                if len(self._buf) > 4096:
                    del self._buf[:-TAMANHO_PACOTE]
        finally:
            try:
                ser.close()
            except Exception:
                pass
            self.fila.put(("status", "Comunicação encerrada"))

    def _extrai_pacotes(self):
        """Consome o buffer devolvendo pacotes de 20 bytes alinhados."""
        pacotes = []
        buf = self._buf
        i = 0
        while len(buf) - i >= TAMANHO_PACOTE:
            if self._sincronizado:
                # Ja alinhado: consome direto, mas revalida para nao perder o passo
                if frame_valido(buf, i):
                    pacotes.append(bytes(buf[i:i + TAMANHO_PACOTE]))
                    i += TAMANHO_PACOTE
                else:
                    self._sincronizado = False
            else:
                if frame_valido(buf, i):
                    pacotes.append(bytes(buf[i:i + TAMANHO_PACOTE]))
                    i += TAMANHO_PACOTE
                    self._sincronizado = True
                else:
                    i += 1  # desliza 1 byte procurando o inicio do pacote
        del buf[:i]
        return pacotes


# ==============================================================================
#  Interface gráfica
# ==============================================================================

COR_FUNDO = "#f2f4f7"
COR_LUZ = "#e8a33d"
COR_RSSI = "#2b7bba"


class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("UL Test - Luminosidade e RSSI")
        self.geometry("1180x760")
        self.minsize(900, 620)
        self.configure(bg=COR_FUNDO)

        self.fila = queue.Queue()
        self.leitor = None
        self.rodando = False
        self.t0 = None

        # Series acumuladas (janela nao deslizante)
        # Eixo X = numero do pacote recebido; o tempo vai apenas para o rodape
        self.n = []
        self.lum = []
        self.rssi = []
        self.n_pacotes = 0

        self._monta_barra_controle()
        self._monta_area_graficos()

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self.after(100, self._processa_fila)
        self.after(250, self._atualiza_graficos)

    # ------------------------------------------------------------------ layout

    def _monta_barra_controle(self):
        barra = tk.Frame(self, bg=COR_FUNDO, padx=14, pady=10)
        barra.pack(side=tk.TOP, fill=tk.X)

        tk.Label(barra, text="Porta serial:", bg=COR_FUNDO,
                 font=("Segoe UI", 11)).pack(side=tk.LEFT)

        self.var_porta = tk.StringVar()
        self.combo_porta = ttk.Combobox(barra, textvariable=self.var_porta,
                                        width=34, state="readonly",
                                        font=("Segoe UI", 10))
        self.combo_porta.pack(side=tk.LEFT, padx=(8, 6))

        self.btn = tk.Button(barra, text="INICIAR", command=self._alterna,
                             font=("Segoe UI", 16, "bold"),
                             bg="#1e9e57", fg="white",
                             activebackground="#178045", activeforeground="white",
                             width=14, height=1, relief=tk.FLAT, cursor="hand2")
        self.btn.pack(side=tk.LEFT, padx=18)

        ttk.Button(barra, text="Limpar graficos",
                   command=self._limpa).pack(side=tk.LEFT)

        self.var_status = tk.StringVar(value="Selecione a porta do Gateway LoRa")
        tk.Label(barra, textvariable=self.var_status, bg=COR_FUNDO,
                 fg="#4a5568", font=("Segoe UI", 10)).pack(side=tk.RIGHT)

        self._itens_porta = None
        self._monitora_portas()

    def _monta_area_graficos(self):
        area = tk.Frame(self, bg=COR_FUNDO, padx=14, pady=4)
        area.pack(fill=tk.BOTH, expand=True)
        area.columnconfigure(0, weight=1)
        area.columnconfigure(1, minsize=230)
        area.rowconfigure(0, weight=1)

        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.fig.subplots_adjust(left=0.09, right=0.98, top=0.95,
                                 bottom=0.08, hspace=0.32)

        self.ax_lum = self.fig.add_subplot(211)
        self.ax_rssi = self.fig.add_subplot(212, sharex=self.ax_lum)

        self.ax_lum.set_title("Luminosidade (LDR)", fontsize=12, fontweight="bold")
        self.ax_lum.set_ylabel("Leitura ADC")
        self.ax_rssi.set_title("RSSI de Uplink", fontsize=12, fontweight="bold")
        self.ax_rssi.set_ylabel("RSSI (dBm)")
        self.ax_rssi.set_xlabel("Pacotes recebidos")

        for ax in (self.ax_lum, self.ax_rssi):
            ax.grid(True, linestyle="--", alpha=0.4)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))

        (self.linha_lum,) = self.ax_lum.plot([], [], color=COR_LUZ, lw=1.8,
                                             marker="o", ms=3)
        (self.linha_rssi,) = self.ax_rssi.plot([], [], color=COR_RSSI, lw=1.8,
                                               marker="o", ms=3)

        self.canvas = FigureCanvasTkAgg(self.fig, master=area)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        lateral = tk.Frame(area, bg=COR_FUNDO, padx=12)
        lateral.grid(row=0, column=1, sticky="nsew")
        lateral.rowconfigure(0, weight=1)
        lateral.rowconfigure(1, weight=1)
        lateral.columnconfigure(0, weight=1)

        self.var_lum = tk.StringVar(value="---")
        self.var_rssi = tk.StringVar(value="---")
        self._card(lateral, 0, "LUMINOSIDADE ATUAL", self.var_lum, "", COR_LUZ)
        self._card(lateral, 1, "RSSI UPLINK ATUAL", self.var_rssi, "dBm", COR_RSSI)

        rodape = tk.Frame(self, bg=COR_FUNDO, padx=14, pady=8)
        rodape.pack(fill=tk.X)
        self.var_info = tk.StringVar(value="Pacotes recebidos: 0")
        tk.Label(rodape, textvariable=self.var_info, bg=COR_FUNDO,
                 fg="#4a5568", font=("Segoe UI", 10)).pack(side=tk.LEFT)

    def _card(self, pai, linha, titulo, variavel, unidade, cor):
        quadro = tk.Frame(pai, bg="white", highlightbackground=cor,
                          highlightthickness=2, padx=12, pady=14)
        quadro.grid(row=linha, column=0, sticky="nsew", pady=10)
        tk.Label(quadro, text=titulo, bg="white", fg="#4a5568",
                 font=("Segoe UI", 9, "bold")).pack()
        tk.Label(quadro, textvariable=variavel, bg="white", fg=cor,
                 font=("Segoe UI", 30, "bold")).pack(pady=(6, 0))
        if unidade:
            tk.Label(quadro, text=unidade, bg="white", fg="#718096",
                     font=("Segoe UI", 11)).pack()

    # ----------------------------------------------------------------- ações

    def _monitora_portas(self):
        """Varre as portas seriais periodicamente (plug/unplug sem ação do usuário)."""
        self._atualiza_portas()
        self.after(1000, self._monitora_portas)

    def _atualiza_portas(self):
        portas = sorted(serial.tools.list_ports.comports(), key=lambda p: p.device)
        itens = [f"{p.device} - {p.description}" for p in portas]
        if itens == self._itens_porta:
            return  # nada mudou: não mexe no combo (evita fechar a lista aberta)
        self._itens_porta = itens

        selecao = self.var_porta.get()
        self.combo_porta["values"] = itens

        if selecao in itens or self.rodando:
            self.var_porta.set(selecao)  # preserva a escolha / a porta em uso
        elif itens:
            self.var_porta.set(itens[0])
        else:
            self.var_porta.set("")

        if not self.rodando:
            self.var_status.set("Selecione a porta do Gateway LoRa" if itens
                                else "Nenhuma porta serial detectada")

    def _porta_selecionada(self):
        texto = self.var_porta.get()
        return texto.split(" - ")[0].strip() if texto else ""

    def _alterna(self):
        if self.rodando:
            self._para()
        else:
            self._inicia()

    def _inicia(self):
        porta = self._porta_selecionada()
        if not porta:
            messagebox.showwarning("Porta serial",
                                   "Selecione uma porta serial antes de iniciar.")
            return
        self.leitor = LeitorSerial(porta, self.fila)
        self.leitor.start()
        self.rodando = True
        if self.t0 is None:
            self.t0 = time.time()
        self.btn.config(text="PARAR", bg="#d94a3d", activebackground="#b73a2f")
        self.combo_porta.config(state="disabled")
        self.var_status.set(f"Abrindo {porta}...")

    def _para(self):
        if self.leitor is not None:
            self.leitor.parar()
            self.leitor = None
        self.rodando = False
        self.btn.config(text="INICIAR", bg="#1e9e57", activebackground="#178045")
        self.combo_porta.config(state="readonly")
        self.var_status.set("Comunicação parada")

    def _limpa(self):
        self.n.clear()
        self.lum.clear()
        self.rssi.clear()
        self.n_pacotes = 0
        self.t0 = time.time() if self.rodando else None
        self.var_lum.set("---")
        self.var_rssi.set("---")
        self.var_info.set("Pacotes recebidos: 0")
        for ax in (self.ax_lum, self.ax_rssi):
            ax.relim()
            ax.autoscale_view()
        self.linha_lum.set_data([], [])
        self.linha_rssi.set_data([], [])
        self.canvas.draw_idle()

    # ------------------------------------------------------------ atualizacao

    def _processa_fila(self):
        try:
            while True:
                tipo, carga = self.fila.get_nowait()
                if tipo == "pacote":
                    self._novo_pacote(carga)
                elif tipo == "status":
                    self.var_status.set(carga)
                elif tipo == "erro":
                    self._para()
                    messagebox.showerror("Erro de comunicação", carga)
        except queue.Empty:
            pass
        self.after(80, self._processa_fila)

    def _novo_pacote(self, dados):
        luminosidade, rssi = dados
        agora = time.time() - (self.t0 or time.time())
        self.n_pacotes += 1
        self.n.append(self.n_pacotes)   # eixo X: numero do pacote recebido
        self.lum.append(luminosidade)
        self.rssi.append(rssi)
        self.var_lum.set(str(luminosidade))
        self.var_rssi.set(f"{rssi:.1f}")
        self.var_info.set(f"Pacotes recebidos: {self.n_pacotes}   |   "
                          f"Tempo de aquisição: {agora:.0f} s")

    def _atualiza_graficos(self):
        if self.n:
            self.linha_lum.set_data(self.n, self.lum)
            self.linha_rssi.set_data(self.n, self.rssi)
            for ax in (self.ax_lum, self.ax_rssi):
                ax.relim()
                ax.autoscale_view()
                # Mantem a janela acumulativa: eixo X sempre desde o 1o pacote
                ax.set_xlim(0, max(self.n[-1] + 1, 10))
            self.canvas.draw_idle()
        self.after(250, self._atualiza_graficos)

    def _ao_fechar(self):
        if self.rodando:
            self._para()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
