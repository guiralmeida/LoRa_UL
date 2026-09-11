// Teste de UPLINK - UL
// Gateway LoRa recebe a cada 1 segundo a luminosidade
// Também mede a potência rádio recebida

// Importação de Bibliotecas
#include <SPI.h>  // Biblioteca de comunicação SPI
#include <LoRa.h> // Biblioteca para o módulo LoRa

// Pinagem Gateway LoRa - ligação do RFM95 com o ESP32
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
#define LED_VERDE_PIN     4            // Pisca ao receber o pacote de UL
#define LED_VERMELHO_PIN 15            // Não utilizado no Gateway (apenas apagado)

// Variáveis Globais e de Configuração
#define TAMANHO_PACOTE 20              // Tamanho do pacote de UL

// Pacotes de Comunicação 
byte Pacote_UL[TAMANHO_PACOTE]; // Pacote de Uplink

// Variáveis de Medição
float rssi_ul_real_dbm; // Armazena o RSSI de Uplink medido (ex: -80.5)
byte rssi_ul_convertido; // Armazena o RSSI convertido para 1 byte (ex: 170)


// ==============================================================================
//  SETUP: Executado uma única vez
// ==============================================================================

void setup() {
  Serial.begin(115200);

// Inicialização de I/O

  pinMode(LED_VERDE_PIN, OUTPUT);
  pinMode(LED_VERMELHO_PIN, OUTPUT);
  
  // Garante que os LEDs iniciem desligados
  digitalWrite(LED_VERDE_PIN, LOW);
  digitalWrite(LED_VERMELHO_PIN, LOW); // LED vermelho totalmente apagado
  
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
  
  // Coloca o rádio LoRa em modo de escuta RX
  LoRa.receive(); 
  // Pisca o LED Verde para indicar inicialização bem-sucedida
  digitalWrite(LED_VERDE_PIN, HIGH);
  delay(1000);
  digitalWrite(LED_VERDE_PIN, LOW);
  // Aguarda 1 segundo para estabilização
  delay(1000);

}


// ==============================================================================
//  LOOP: Executado continuamente
// ==============================================================================

void loop() {
   
   // ----------------------------------------------------------------------------
   // FLUXO DE RECEBIMENTO (UPLINK): Rádio LoRa -> USB
   // ----------------------------------------------------------------------------
  
   // Checagem de pacote UL
   uint8_t packetSize = LoRa.parsePacket();

   if (packetSize > 0) { // Caso identificado um pacote

      if (packetSize >= TAMANHO_PACOTE) { // O pacote possui o tamanho de Bytes do Pacote
    
         // Leitura do pacote de UL no RFM95
         for (int i = 0; i < TAMANHO_PACOTE; i++)
         {
            Pacote_UL[i] = LoRa.read();
         }
  
         // Leitura potêmcia rádio recedida pelo RFM95 - RSSI 
         rssi_ul_real_dbm = LoRa.packetRssi();

         // Converte o RSSI (ex: -80.5) para 1 byte (0-255)
         if(rssi_ul_real_dbm > -10.5)
         {
            rssi_ul_convertido = 127;
         }
         else if(rssi_ul_real_dbm <= -10.5 && rssi_ul_real_dbm >= -74)
         {
            rssi_ul_convertido = ((rssi_ul_real_dbm + 74)*2) ;
         }
         else if(rssi_ul_real_dbm < -74)
         {
            rssi_ul_convertido = (((rssi_ul_real_dbm + 74)*2) + 256) ;
         }

         // Aloca no pacote de UL a RSSI
         Pacote_UL[2] = rssi_ul_convertido;
         Pacote_UL[0] = rssi_ul_convertido;

         // Envia pacote UL pela USB
         for (int i = 0; i < TAMANHO_PACOTE; i++)
         {
            Serial.write(Pacote_UL[i]);
            digitalWrite(LED_VERDE_PIN, HIGH); // Apaga LED verde enquando recebe o pacote
            delay(1);
         }
      } 
      digitalWrite(LED_VERDE_PIN, LOW); // Acende o LED verde para próximo pacote UL
   }
} // Fim do loop()
