// Teste de UPLINK - UL
// Nó sensor LoRa transmite a cada 1 segundo a luminosidade
// Também mede a potência rádio recebida

//Importação de Bibliotecas
#include <SPI.h>  // Biblioteca de comunicação SPI
#include <LoRa.h> // Biblioteca para o módulo LoRa

// Pinagem Nó Sensor LoRa - ligação do RFM95 com o ESP32
#define SCK_PIN    5
#define MISO_PIN  19
#define MOSI_PIN  27
#define NSS_PIN   18
#define RST_PIN   14
#define DIO0_PIN  26

// Parâmetros do LoRa
#define FREQUENCY_IN_HZ       903E6    // Frequência de operação do LoRa
#define txPower               17       // Potência de transmissão do LoRa 17 dBm
#define spreadingFactor       7        // Fator de espalhamento
#define signalBandwidth       125E3    // Largura de faixa em HZ
#define codingRateDenominator 8        // Denominador coding rate

// Definição de Pinos (Hardware)
#define LED_VERMELHO_PIN 15           // Status ENVIO pelo rádio
#define LDR_PIN          36           // Sensor de luminosidade

// Tamanho fixo do pacote (bytes)
#define TAMANHO_PACOTE 20             // Tamanho do pacote de UL

// Pacotes de Comunicação
byte Pacote_UL[TAMANHO_PACOTE]; // Pacote de Uplink

// Variáveis de medição
int luminosidade; // Leitura LDR
int contador_pacotes = 0;


// ==============================================================================
//  SETUP: Executado uma Única vez
// ==============================================================================

void setup() {
  Serial.begin(115200);

  // Inicialização de I/
  pinMode(LED_VERMELHO_PIN, OUTPUT); // LED vermelho pisca quando transmite
  
  // Garante que os LEDs iniciem desligados
  digitalWrite(LED_VERMELHO_PIN, LOW);
  
  // Inicialização da Comunicação SPI entre o ESP32 e o Módulo LoRa RFM95
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, NSS_PIN);
  LoRa.setPins(NSS_PIN, RST_PIN, DIO0_PIN);
  if (!LoRa.begin(FREQUENCY_IN_HZ)) {
    Serial.println("Erro ao iniciar módulo RFM95");
  }
  
  // Configura parâmetros do LoRa no RFM95
  LoRa.setTxPower(txPower);
  LoRa.setSpreadingFactor(spreadingFactor);
  LoRa.setSignalBandwidth(signalBandwidth);
  LoRa.setCodingRate4(codingRateDenominator);
  
  // Pisca o LED Vermelho para indicar inicialização bem-sucedida
  digitalWrite(LED_VERMELHO_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_VERMELHO_PIN, LOW);

} // FIM do SETUP


// ==============================================================================
//  LOOP: Executado continuamente
// ==============================================================================

void loop() {

      // ------------------------------------------------------------------------
      // FLUXO DE ENVIO (Pacote de UPLINK - Nó-Sensor -> Gateway LoRa):
      // ------------------------------------------------------------------------
      
      digitalWrite(LED_VERMELHO_PIN, LOW);
      // Zera o valor dos Bytes do pacote de UL
      for (int i = 0; i < TAMANHO_PACOTE; i++)
      {
         Pacote_UL[i] = 0;
      }
 
      // Coleta e armazena o Valor do Sensor de Intensidade Luminosa - LDR
      luminosidade = analogRead(LDR_PIN); // LÊ LDR (0-1023)
      
      // Debug - escreve no Arduino Serial Monitor o valor coletado de Luminosidade
      Serial.println(luminosidade);     

      // Contador de pacotes de UL
      contador_pacotes = contador_pacotes + 1;

      // Aloca no pacote o valor da luminosidade bytes 18 (inteiro) e 19 (resto)
      Pacote_UL[18] = (byte) (luminosidade / 256); // Byte Alto (MSB)
      Pacote_UL[19] = (byte) (luminosidade % 256); // Byte Baixo (LSB)

      // Aloca no pacote o contador de pacotes bytes 12 (inteiro) e 13 (resto)
      Pacote_UL[12] = (byte) (contador_pacotes / 256); // Byte Alto (MSB)
      Pacote_UL[13] = (byte) (contador_pacotes % 256); // Byte Baixo (LSB)

      LoRa.beginPacket(); // Inicia o RFM95
      for (int i = 0; i < TAMANHO_PACOTE; i++)
      {
        LoRa.write(Pacote_UL[i]); // Escreve na SPI o pacote de UL
        digitalWrite(LED_VERMELHO_PIN, HIGH); // LED vermelho permanece aceso enquanto envia pela SPI
      }
      LoRa.endPacket(); // Finaliza transmissão do pacote UL
      delay(10);
      digitalWrite(LED_VERMELHO_PIN, LOW);
  
      delay(1000); // Aguarda 1 segundos para envio de uma nova leitura
          
} // Fim do loop()