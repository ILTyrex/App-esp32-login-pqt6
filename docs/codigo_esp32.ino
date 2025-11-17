/*************  BLYNK CONFIG  *************/
#define BLYNK_TEMPLATE_ID "TMPL23ObRzr_p"
#define BLYNK_TEMPLATE_NAME "test"
#define BLYNK_AUTH_TOKEN "1yABWzFqZjrQQuFA3djFakvdUPuvYuAF"
#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Keypad.h>
#include <Wire.h>
#include <LiquidCrystal_PCF8574.h>
#include <BlynkSimpleEsp32.h>

LiquidCrystal_PCF8574 lcd(0x27);

// BOTONES
const int BTN1 = 35; // BLUE
const int BTN2 = 34; // RED
const int BTN3 = 39; // GREEN

// SENSOR
const int SENSOR = 23;
bool sensorState = false;
bool lastSensorActivo = false;
int lastSensorState;

// LEDS
const int LED1 = 16; // BLUE
const int LED2 = 17; // RED
const int LED3 = 5;  // GREEN
const int LED4 = 22; // YELLOW

// LCD (I2C)
const int LCD1 = 19; // SDA
const int LCD2 = 21; // SCL

// Estados de leds
bool stateLed1 = false;
bool stateLed2 = false;
bool stateLed3 = false;
bool stateLed4 = false;

// Último evento web procesado
unsigned long lastEventPoll = 0;
const unsigned long EVENT_POLL_INTERVAL = 2000; // ms
long lastEventId = 0;

// Estados anteriores botones
bool lastBtn1 = LOW;
bool lastBtn2 = LOW;
bool lastBtn3 = LOW;

int counter = 0;
int currentMenu = 0;     // 0 = menú principal, 1 = LED, 2 = Sensor, 3 = Estado BD
String currentUser = ""; // Nombre del usuario logueado

// Wifi
const char *ssid = "DANIEL"; // wifi
const char *password = "1974mia@"; // Contraseña del hotspot
const char *baseUrl = "http://10.92.129.180:5000"; // IP actual
bool wifiConnected = false;
unsigned long lastWiFiCheck = 0;

// TECLADO MATRICIAL
const byte ROWS = 4;
const byte COLS = 4;
char keys[ROWS][COLS] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'}};
byte rowPins[ROWS] = {13, 12, 14, 27}; // Filas
byte colPins[COLS] = {26, 25, 33, 32}; // Columnas
Keypad keypad = Keypad(makeKeymap(keys), rowPins, colPins, ROWS, COLS);

/*************  THINGSPEAK CONFIG  *************/
const char* thingSpeakServer = "api.thingspeak.com";
const char* thingSpeakApiKey = "XL83F0HE31DAECM7";
const unsigned long thingSpeakChannel = 3163824;
unsigned long lastThingSpeakUpdate = 0;
const unsigned long THINGSPEAK_INTERVAL = 10000;

void sendToThingSpeak() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi no conectado - no se puede enviar a ThingSpeak");
    return;
  }

  HTTPClient http;

  // Construir URL con todos los campos
  String url = "https://";
  url += thingSpeakServer;
  url += "/update?api_key=";
  url += thingSpeakApiKey;
  url += "&field1=";
  url += stateLed1 ? "1" : "0";  // LED1
  url += "&field2=";
  url += stateLed2 ? "1" : "0";  // LED2
  url += "&field3=";
  url += stateLed3 ? "1" : "0";  // LED3
  url += "&field4=";
  url += stateLed4 ? "1" : "0";  // LED4_sensor
  url += "&field5=";
  url += String(counter);         // Contador

  Serial.println("Enviando a ThingSpeak: " + url);

  http.begin(url);
  int httpCode = http.GET();

  if (httpCode > 0) {
    String payload = http.getString();
    Serial.println("ThingSpeak respuesta: " + payload);

    // Si devuelve un número (1,2,3,etc) significa éxito
    if (payload.toInt() > 0) {
      Serial.println("✓ Datos enviados exitosamente a ThingSpeak");
    } else {
      Serial.println("✗ Error en ThingSpeak: " + payload);
    }
  } else {
    Serial.println("✗ Error HTTP al conectar con ThingSpeak: " + String(httpCode));
  }

  http.end();
}

// Funciones LCD
void showWelcomeUser()
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Bienvenido:");
  lcd.setCursor(0, 1);
  if (currentUser.length() > 0)
  {
    lcd.print(currentUser);
  }
  else
  {
    lcd.print("Usuario N/D"); // Por si no hay nombre aún
  }
}
void showMainMenu()
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("1-Leds");
  lcd.setCursor(8, 0);
  lcd.print("2-Sensor");
  lcd.setCursor(2, 1);
  lcd.print("3-Estado BD");
}
// Menus
void showLedMenu()
{
  lcd.clear();
  lcd.setCursor(2, 0);
  lcd.print("1-ON");
  lcd.setCursor(9, 0);
  lcd.print("2-OFF");
  lcd.setCursor(3, 1);
  lcd.print("3-Estados");
}
void showSensorMenu()
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("1-Estado");
  lcd.setCursor(0, 1);
  lcd.print("2-Conteo");
}
void showEstadoBDMenu()
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Mostrando ultimos");
  lcd.setCursor(0, 1);
  lcd.print("5 estados...");
}

// Formatea un evento para mostrar en 16 caracteres: "U{user} {detalle} {valor}"
/* String formatEventForLCD(const String &user, const String &detalle, const String &valor)
{
  String s = "U" + user + " " + detalle + " " + valor;
  // Acortar si supera 16 caracteres
  if (s.length() > 16)
  {
    s = s.substring(0, 16);
  }
  return s;
}

// Obtiene los últimos 5 eventos del servidor y los muestra en el LCD con una animación "subiendo"
void fetchAndShowLastEvents()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi no conectado");
    delay(1000);
    showEstadoBDMenu();
    return;
  }

  HTTPClient http;
  String url = String(baseUrl) + "/api/esp32/get-data";
  http.begin(url);
  int httpCode = http.GET();
  if (httpCode != HTTP_CODE_OK)
  {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Error al obtener");
    lcd.setCursor(0, 1);
    lcd.print("eventos");
    http.end();
    delay(1000);
    showEstadoBDMenu();
    return;
  }

  String payload = http.getString();
  http.end();

  StaticJsonDocument<1024> doc;
  DeserializationError err = deserializeJson(doc, payload);
  if (err)
  {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("JSON error");
    delay(1000);
    showEstadoBDMenu();
    return;
  }

  JsonArray arr = doc["events"].as<JsonArray>();
  if (!arr || arr.size() == 0)
  {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Sin eventos");
    delay(1000);
    showEstadoBDMenu();
    return;
  }

  // Asegurar que procesamos en orden cronológico (del más antiguo al más reciente)
  int n = arr.size();
  int start = max(0, n - 5);

  // Construir líneas numeradas (1..k) sin mostrar el id de usuario
  String lines[5];
  int idx = 0;
  for (int i = start; i < n && idx < 5; i++)
  {
    JsonObject ev = arr[i];
    String detalle = String(ev["detalle"] | "");
    String valor = String(ev["valor"] | "");
    // Formato: "{num} {detalle} {valor}" (sin id_usuario)
    String content = String(idx + 1) + " " + detalle + " " + valor;
    if (content.length() > 16)
      content = content.substring(0, 16);
    lines[idx++] = content;
  }

  // Primera muestra: título "EVENTOS" y el evento 1
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("EVENTOS");
  if (idx >= 1)
  {
    lcd.setCursor(0, 1);
    lcd.print(lines[0]);
  }
  delay(1500);

  // Segunda muestra: mostrar eventos 2 y 3 (si existen)
  if (idx >= 2)
  {
    lcd.clear();
    if (idx >= 2)
      lcd.setCursor(0, 0), lcd.print(lines[1]);
    if (idx >= 3)
      lcd.setCursor(0, 1), lcd.print(lines[2]);
    delay(1500);
  }

  // Tercera muestra: mostrar eventos 4 y 5 (si existen)
  if (idx >= 4)
  {
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(lines[3]);
    if (idx >= 5)
    {
      lcd.setCursor(0, 1);
      lcd.print(lines[4]);
    }
    delay(1500);
  }

  // Finalmente, volver al menú principal (0)
  currentMenu = 0;
  showMainMenu();
}

*/

void showLedStates()
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("LED1 LED2 LED3");
  lcd.setCursor(0, 1);
  lcd.print(stateLed1 ? " ON" : "OFF");
  lcd.setCursor(5, 1);
  lcd.print(stateLed2 ? " ON" : "OFF");
  lcd.setCursor(10, 1);
  lcd.print(stateLed3 ? " ON" : "OFF");
}

void showSensorStates()
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("SENSOR");
  lcd.setCursor(12, 0);
  lcd.print("LED4");
  lcd.setCursor(0, 1);
  lcd.print(sensorState ? "Bloqueado" : "Libre");
  lcd.setCursor(12, 1);
  lcd.print(stateLed4 ? " ON" : "OFF");
}
void showCounter()
{
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("CONTEO");
  lcd.setCursor(0, 1);
  lcd.print(counter);
  lcd.setCursor(12, 0);
  lcd.print("LED4");
  lcd.setCursor(12, 1);
  lcd.print(stateLed4 ? " ON" : "OFF");
}

// Funciones Wifi y Http
void connectWiFi()
{
  WiFi.begin(ssid, password);
  Serial.println("Intentando conectar a WiFi...");
}
void checkWiFiStatus()
{
  // Solo verificar cada 2 segundos para no saturar
  if (millis() - lastWiFiCheck > 2000)
  {
    lastWiFiCheck = millis();

    if (WiFi.status() == WL_CONNECTED && !wifiConnected)
    {
      wifiConnected = true;
      Serial.println("WiFi conectado!");
      Serial.print("IP: ");
      Serial.println(WiFi.localIP());

      lcd.clear();
      lcd.setCursor(0, 0);
      lcd.print("Conectado WiFi");
      lcd.setCursor(0, 1);
      lcd.print(WiFi.localIP());
      delay(1500);
      showMainMenu(); // Regresa al menú principal
    }
  }
}


/* void sendEvent(String tipo_evento, String detalle, String valor)
{
  if (WiFi.status() == WL_CONNECTED)
  {
    HTTPClient http;
    StaticJsonDocument<200> jsonDoc;

    jsonDoc["id_usuario"] = 1;            // puedes dejar 1 o un valor fijo
    jsonDoc["tipo_evento"] = tipo_evento; // ejemplo: "LED_ON"
    jsonDoc["detalle"] = detalle;         // ejemplo: "LED1"
    jsonDoc["origen"] = "CIRCUITO";       // indica que viene del ESP32
    jsonDoc["valor"] = valor;             // ejemplo: "ON" o "OFF"

    String jsonString;
    serializeJson(jsonDoc, jsonString);

    http.begin(String(baseUrl) + "/api/esp32/data");
    http.addHeader("Content-Type", "application/json");
    int httpResponseCode = http.POST(jsonString);

    if (httpResponseCode > 0)
    {
      Serial.println("Evento enviado OK");
    }
    else
    {
      Serial.println("Error al enviar evento");
    }
    http.end();
  }
  else
  {
    Serial.println("WiFi no conectado, no se puede enviar evento");
  }
}

*/

void sendCounter()
{
  //sendEvent("CONTADOR_CAMBIO", "CONTADOR", String(counter));
  Blynk.virtualWrite(V4, counter);
}


bool localChange = false;

void updateLed(int ledNum, bool estado)
{
  String ledStr = "LED" + String(ledNum);
  String estadoStr = estado ? "ON" : "OFF";

  // Enviar evento HTTP solo si hay WiFi
  if (WiFi.status() == WL_CONNECTED) {
    //sendEvent("LED_" + estadoStr, ledStr, estadoStr);
  }

  // IMPORTANTE: Marcar que este cambio viene del ESP32
  localChange = true;

  // Actualizar Blynk
  if (ledNum >= 1 && ledNum <= 4) {
    Blynk.virtualWrite(V0 + (ledNum - 1), estado ? 1 : 0);
  }

  // Restaurar la bandera después de un breve delay
  delay(10);
  localChange = false;
}

BLYNK_WRITE(V0) {

  if (localChange) return;

  int value = param.asInt();
  stateLed1 = value;
  digitalWrite(LED1, value ? HIGH : LOW);
  Serial.println("Blynk LED1: " + String(value));

  // Actualizar pantalla si estamos en menú de LEDs
  if (currentMenu == 1 || currentMenu == 4) {
    showLedStates();
    if (currentMenu == 1) {
      delay(50);
      showLedMenu();
    }
  }
}

BLYNK_WRITE(V1) {
  if (localChange) return;

  int value = param.asInt();
  stateLed2 = value;
  digitalWrite(LED2, value ? HIGH : LOW);
  Serial.println("Blynk LED2: " + String(value));

  if (currentMenu == 1 || currentMenu == 4) {
    showLedStates();
    if (currentMenu == 1) {
      delay(50);
      showLedMenu();
    }
  }
}

BLYNK_WRITE(V2) {
  if (localChange) return;

  int value = param.asInt();
  stateLed3 = value;
  digitalWrite(LED3, value ? HIGH : LOW);
  Serial.println("Blynk LED3: " + String(value));

  if (currentMenu == 1 || currentMenu == 4) {
    showLedStates();
    if (currentMenu == 1) {
      delay(50);
      showLedMenu();
    }
  }
}

BLYNK_WRITE(V3) {
  if (localChange) return;

  int value = param.asInt();
  stateLed4 = value;
  digitalWrite(LED4, value ? HIGH : LOW);
  Serial.println("Blynk LED4: " + String(value));
}

BLYNK_WRITE(V6) {
  int value = param.asInt();
  if (value == 1) {
    counter = 0;
    Blynk.virtualWrite(V4, 0);
    Serial.println("Blynk: Contador reseteado");

    if (WiFi.status() == WL_CONNECTED) {
      //sendEvent("RESET_CONTADOR", "CONTADOR", "0");
    }

    // Actualizar pantalla si estamos en menú de contador
    if (currentMenu == 6) {
      showCounter();
    }
  }
}

void updateBlynkSensor() {
  Blynk.virtualWrite(V5, sensorState ? 1 : 0);
}

/*
 void pollLastEvent()
{
  if (WiFi.status() != WL_CONNECTED)
    return;

  HTTPClient http;
  String url = String(baseUrl) + "/api/esp32/last-event";
  http.begin(url);
  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK)
  {
    String payload = http.getString();
    http.end();
    StaticJsonDocument<512> doc;
    DeserializationError err = deserializeJson(doc, payload);
    if (!err)
    {
      if (!doc["event"].isNull())
      {
        JsonObject ev = doc["event"];
        long id = ev["id_evento"] | 0;
        String detalle = String(ev["detalle"] | "");
        String valor = String(ev["valor"] | "");
        String tipo = String(ev["tipo_evento"] | "");

        // Normalizar y limpiar strings para evitar problemas de formato
        detalle.trim();
        valor.trim();
        tipo.trim();
        detalle.toUpperCase();
        valor.toUpperCase();
        tipo.toUpperCase();

        if (id != lastEventId && id != 0)
        {
          lastEventId = id;
          Serial.println("WEBCMD: id=" + String(id) + " detalle=" + detalle + " valor=" + valor);

          // Determinar si debe encenderse
          bool setOn = (valor == "ON" || valor == "1" || valor == "TRUE");

          // Manejar reset de contador enviado desde la WEB
          bool handledReset = false;
          if (tipo == "RESET_CONTADOR" || (detalle.indexOf("CONTADOR") >= 0 && (valor == "RESET" || valor == "0")))
          {
            // Solo aplicar el reset si estamos en los menús de sensor (5 o 6).
            if (currentMenu == 5 || currentMenu == 6)
            {
              // Aplicar reset localmente en ESP32: contador y pantalla
              counter = 0;
              Serial.println("APPLIED WEB -> RESET_CONTADOR: counter set to 0");
              showCounter();
              // Registrar que procesamos este evento
              lastEventId = id;
              handledReset = true;
            }
            else
            {
              // Ignorar por ahora; no marcamos lastEventId para que se procese cuando
              // el usuario esté en el menú 5 o 6 en un poll futuro.
              Serial.println(String("IGNORED WEB -> RESET_CONTADOR: currentMenu=") + String(currentMenu));
            }
          }

          // Manejar login enviado desde la WEB: mostrar usuario en LCD
          if (tipo == "LOGIN")
          {
            String user = valor;
            user.trim();
            if (user.length() > 0)
            {
              // Guardar usuario y mostrar mensaje de bienvenida temporalmente
              currentUser = user;
              Serial.println(String("APPLIED WEB -> LOGIN: ") + currentUser);
              int prevMenu = currentMenu; // recordar menú actual
              showWelcomeUser();
              delay(1500);

              // Restaurar la vista según el menú en el que estábamos
              if (prevMenu == 0)
                showMainMenu();
              else if (prevMenu == 1)
                showLedMenu();
              else if (prevMenu == 4)
                showLedStates();
              else if (prevMenu == 2)
                showSensorMenu();
              else if (prevMenu == 5 || prevMenu == 6)
                showCounter();

              // Marcar evento como procesado
              lastEventId = id;
              // continue with loop (do not process as LED/reset)
            }
          }

          // Si no fue un reset, procesar comandos de LED
          if (!handledReset)
          {
            // Extraer número de LED del campo detalle de forma robusta (acepta "LED1", "LED 1", "led-1", etc.)
            int ledNum = 0;
            for (unsigned int i = 0; i < detalle.length(); i++)
            {
              char c = detalle.charAt(i);
              if (c >= '0' && c <= '9')
              {
                ledNum = ledNum * 10 + (c - '0');
              }
            }

            // Si no se detectó número, intentar parsear formas tipo "LED1" (fallback)
            if (ledNum == 0 && detalle.startsWith("LED"))
            {
              ledNum = detalle.substring(3).toInt();
            }

            // Aplicar cambio físico SOLO si estamos en los menús permitidos (1 o 4).
            // Si no, ignorar el comando web para evitar que los LEDs cambien fuera de esos menús.
            if (ledNum >= 1 && ledNum <= 4)
            {
              if (currentMenu == 1 || currentMenu == 4)
              {
                if (ledNum == 1)
                {
                  digitalWrite(LED1, setOn ? HIGH : LOW);
                  stateLed1 = setOn;
                  Serial.println(String("APPLIED WEB -> LED1: ") + (setOn ? "ON" : "OFF"));
                }
                else if (ledNum == 2)
                {
                  digitalWrite(LED2, setOn ? HIGH : LOW);
                  stateLed2 = setOn;
                  Serial.println(String("APPLIED WEB -> LED2: ") + (setOn ? "ON" : "OFF"));
                }
                else if (ledNum == 3)
                {
                  digitalWrite(LED3, setOn ? HIGH : LOW);
                  stateLed3 = setOn;
                  Serial.println(String("APPLIED WEB -> LED3: ") + (setOn ? "ON" : "OFF"));
                }
                else if (ledNum == 4)
                {
                  digitalWrite(LED4, setOn ? HIGH : LOW);
                  stateLed4 = setOn;
                  Serial.println(String("APPLIED WEB -> LED4: ") + (setOn ? "ON" : "OFF"));
                }

                // Refrescar la UI donde corresponda (si estamos viendo LEDs o sensor)
                if (currentMenu == 4)
                {
                  showLedStates();
                }
                else if (currentMenu == 1)
                {
                  // Mantener la navegación pero refrescar la información
                  showLedStates();
                  delay(500);
                  showLedMenu();
                }
                else if (currentMenu == 2 || currentMenu == 5 || currentMenu == 6)
                {
                  showSensorStates();
                }
              }
              else
              {
                // Ignorar comando web: no estamos en menú 1 ni 4
                Serial.println(String("IGNORED WEB -> LED") + String(ledNum) + ": currentMenu=" + String(currentMenu));
              }
            }
          }
          else
          {
            Serial.println("WEBCMD: detalle no corresponde a LED valido -> " + detalle);
          }
        }
      }
    }
    else
    {
      Serial.println("pollLastEvent: JSON parse error");
    }
  }
  else
  {
    http.end();
  }
}
*/

void setup()
{
  Serial.begin(115200);
  Serial.println("Starting LCD...");

  Wire.begin(LCD1, LCD2);

  lcd.begin(16, 2);
  lcd.setBacklight(255);

  pinMode(BTN1, INPUT);
  pinMode(BTN2, INPUT);
  pinMode(BTN3, INPUT);
  pinMode(SENSOR, INPUT);

  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);
  pinMode(LED3, OUTPUT);
  pinMode(LED4, OUTPUT);

  digitalWrite(LED1, LOW);
  digitalWrite(LED2, LOW);
  digitalWrite(LED3, LOW);
  digitalWrite(LED4, LOW);

  lastSensorState = digitalRead(SENSOR);

  // Conectar WiFi primero
  WiFi.begin(ssid, password);
  Serial.println("Conectando a WiFi...");

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

   if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi conectado!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());

    // Conectar a Blynk
    Blynk.config(BLYNK_AUTH_TOKEN);
    Blynk.connect();

    delay(1000); // Esperar conexión Blynk
    Blynk.virtualWrite(V0, stateLed1 ? 1 : 0);
    Blynk.virtualWrite(V1, stateLed2 ? 1 : 0);
    Blynk.virtualWrite(V2, stateLed3 ? 1 : 0);
    Blynk.virtualWrite(V3, stateLed4 ? 1 : 0);
    Blynk.virtualWrite(V4, counter);
    Blynk.virtualWrite(V5, sensorState ? 1 : 0);

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi + Blynk OK");
    lcd.setCursor(0, 1);
    lcd.print(WiFi.localIP());
    delay(2000);
  } else {
    Serial.println("\nError: No se pudo conectar al WiFi");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi ERROR");
    delay(2000);
  }

  showMainMenu();
}

void loop()
{
  // Mantener Blynk conectado
  Blynk.run();

  checkWiFiStatus();

  // LECTURA BOTONES
  bool btn1 = digitalRead(BTN1);
  bool btn2 = digitalRead(BTN2);
  bool btn3 = digitalRead(BTN3);

  char key = keypad.getKey();
  if (currentMenu == 0)
  {
    if (key)
    {
      Serial.println(String("Opción seleccionada: ") + key);
      if (key == '1')
      {
        currentMenu = 1;
        showLedMenu();
        key = '\0';
      }
      else if (key == '2')
      {
        currentMenu = 2;
        showSensorMenu();
        key = '\0';
      }
      else if (key == '3')
      {
        currentMenu = 3;
        showEstadoBDMenu();
        // Obtener y mostrar últimos 5 eventos con animación
        //fetchAndShowLastEvents();
        //key = '\0';
      }
    }
  }
  else
  {
    // Si estamos dentro de un submenú, presiona * para volver al principal
    if (key == '*')
    {
      currentMenu = 0;
      showMainMenu();
      key = '\0';
    }
  }

  // Leds
  if (currentMenu == 1)
  {
    if (key)
    {
      if (key == '1')
      {
        // Encender todos los LEDs
        stateLed1 = stateLed2 = stateLed3 = true;
        digitalWrite(LED1, HIGH);
        digitalWrite(LED2, HIGH);
        digitalWrite(LED3, HIGH);
        Serial.println("ACK:LED:1:" + String(stateLed1 ? "1" : "0"));
        Serial.println("ACK:LED:2:" + String(stateLed2 ? "1" : "0"));
        Serial.println("ACK:LED:3:" + String(stateLed3 ? "1" : "0"));
        updateLed(1, stateLed1);
        updateLed(2, stateLed2);
        updateLed(3, stateLed3);
        showLedStates();
        delay(100);
        showLedMenu();
      }
      else if (key == '2')
      {
        // Apagar todos los LEDs
        stateLed1 = stateLed2 = stateLed3 = false;
        digitalWrite(LED1, LOW);
        digitalWrite(LED2, LOW);
        digitalWrite(LED3, LOW);
        Serial.println("ACK:LED:1:" + String(stateLed1 ? "1" : "0"));
        Serial.println("ACK:LED:2:" + String(stateLed2 ? "1" : "0"));
        Serial.println("ACK:LED:3:" + String(stateLed3 ? "1" : "0"));
        updateLed(1, stateLed1);
        updateLed(2, stateLed2);
        updateLed(3, stateLed3);
        showLedStates();
        delay(100);
        showLedMenu();
      }
      else if (key == '3')
      {
        // Mostrar estados actuales
        currentMenu = 4;
        showLedStates();
        Serial.println("Mostrando estados de LEDs. Presiona * para volver.");
        key = '\0';
      }
    }
    if (lastBtn1 == LOW && btn1 == HIGH)
    {
      stateLed1 = !stateLed1;
      digitalWrite(LED1, stateLed1);
      Serial.println("ACK:LED:1:" + String(stateLed1 ? "1" : "0"));
      updateLed(1, stateLed1);
      // Actualizar LCD para reflejar el nuevo estado (igual que al cambiar por teclado)
      showLedStates();
      delay(100);
      showLedMenu();
    }
    lastBtn1 = btn1;

    if (lastBtn2 == LOW && btn2 == HIGH)
    {
      stateLed2 = !stateLed2;
      digitalWrite(LED2, stateLed2);
      Serial.println("ACK:LED:2:" + String(stateLed2 ? "1" : "0"));
      updateLed(2, stateLed2);
      // Actualizar LCD para reflejar el nuevo estado (igual que al cambiar por teclado)
      showLedStates();
      delay(100);
      showLedMenu();
    }
    lastBtn2 = btn2;

    if (lastBtn3 == LOW && btn3 == HIGH)
    {
      stateLed3 = !stateLed3;
      digitalWrite(LED3, stateLed3);
      Serial.println("ACK:LED:3:" + String(stateLed3 ? "1" : "0"));
      updateLed(3, stateLed3);
      // Actualizar LCD para reflejar el nuevo estado (igual que al cambiar por teclado)
      showLedStates();
      delay(100);
      showLedMenu();
    }
    lastBtn3 = btn3;
  }

  // Submenú: Estados de LEDs
  if (currentMenu == 4)
  {
    // Permitir encender LEDs desde el teclado matricial mientras estamos en el menú de estados
    if (key)
    {
      if (key == '1')
      {
        // Toggle LED1
        stateLed1 = !stateLed1;
        digitalWrite(LED1, stateLed1 ? HIGH : LOW);
        Serial.println("ACK:LED:1:" + String(stateLed1 ? "1" : "0"));
        updateLed(1, stateLed1);
        showLedStates();
        key = '\0';
      }
      else if (key == '2')
      {
        // Toggle LED2
        stateLed2 = !stateLed2;
        digitalWrite(LED2, stateLed2 ? HIGH : LOW);
        Serial.println("ACK:LED:2:" + String(stateLed2 ? "1" : "0"));
        updateLed(2, stateLed2);
        showLedStates();
        key = '\0';
      }
      else if (key == '3')
      {
        // Toggle LED3
        stateLed3 = !stateLed3;
        digitalWrite(LED3, stateLed3 ? HIGH : LOW);
        Serial.println("ACK:LED:3:" + String(stateLed3 ? "1" : "0"));
        updateLed(3, stateLed3);
        showLedStates();
        key = '\0';
      }
    }

    if (key == '#')
    {
      currentMenu = 1;
      showLedMenu();
    }
    if (lastBtn1 == LOW && btn1 == HIGH)
    {
      stateLed1 = !stateLed1;
      digitalWrite(LED1, stateLed1);
      Serial.println("ACK:LED:1:" + String(stateLed1 ? "1" : "0"));
      updateLed(1, stateLed1);
      showLedStates();
      delay(300);
    }
    lastBtn1 = btn1;

    if (lastBtn2 == LOW && btn2 == HIGH)
    {
      stateLed2 = !stateLed2;
      digitalWrite(LED2, stateLed2);
      Serial.println("ACK:LED:2:" + String(stateLed2 ? "1" : "0"));
      updateLed(2, stateLed2);
      showLedStates();
      delay(300);
    }
    lastBtn2 = btn2;

    if (lastBtn3 == LOW && btn3 == HIGH)
    {
      stateLed3 = !stateLed3;
      digitalWrite(LED3, stateLed3);
      Serial.println("ACK:LED:3:" + String(stateLed3 ? "1" : "0"));
      updateLed(3, stateLed3);
      showLedStates();
      delay(300);
    }
    lastBtn3 = btn3;
  }

  // SENSOR
  if (currentMenu == 2)
  { // Menú Sensor principal
    if (key)
    {
      if (key == '1')
      {
        currentMenu = 5;
        showSensorStates();
        Serial.println("Mostrando estado de sensor. Presiona # para volver.");
        key = '\0';
      }
      else if (key == '2')
      {
        // Mostrar el conteo actual del sensor
        currentMenu = 6;
        showCounter();
        Serial.println("Mostrando conteo. Presiona # para volver.");
        key = '\0';
      }
    }
  }
  if (currentMenu == 5 || currentMenu == 6)
  {
    int lecturaSensor = digitalRead(SENSOR);
    bool sensorActivo = (lecturaSensor == LOW);
    digitalWrite(LED4, sensorActivo ? HIGH : LOW);
    stateLed4 = sensorActivo;
    // Enviar el estado del LED4 a la web cuando cambie, igual que en el menú de LEDs
    if (sensorActivo != lastSensorActivo)
    {
      Serial.println("ACK:LED:4:" + String(stateLed4 ? "1" : "0"));
      updateLed(4, stateLed4);
    }

    if (currentMenu == 5)
    {
      // Solo mostrar si cambió el estado
      if (sensorActivo != sensorState)
      {
        sensorState = sensorActivo;
        Serial.println(sensorState ? "SENSOR:1" : "SENSOR:0");
        showSensorStates();
        String tipo_evento = sensorState ? "SENSOR_BLOQUEADO" : "SENSOR_LIBRE";
        String valor = sensorState ? "ON" : "OFF";

        //sendEvent(tipo_evento, "SENSOR_IR", valor);
        Blynk.virtualWrite(V5, sensorState ? 1 : 0);
      }
      if (sensorActivo && !lastSensorActivo)
      {
        counter++;
        sendCounter();
      }
    }
    if (currentMenu == 6)
    {

      if (sensorActivo != sensorState)
      {
        sensorState = sensorActivo;
        Serial.println(sensorState ? "SENSOR:1" : "SENSOR:0");
        showCounter();

        String tipo_evento = sensorState ? "SENSOR_BLOQUEADO" : "SENSOR_LIBRE";
        String valor = sensorState ? "ON" : "OFF";
        //sendEvent(tipo_evento, "SENSOR_IR", valor);
        Blynk.virtualWrite(V5, sensorState ? 1 : 0);

      }

      // Lógica de conteo: si el sensor pasó de no activo a activo incrementa el contador
      if (sensorActivo && !lastSensorActivo)
      {
        Serial.println("SENSOR:1");
        counter++;
        sendCounter();
        showCounter();
      }
      if (!sensorActivo && lastSensorActivo)
      {
        Serial.println("SENSOR:0");
        showCounter();
      }
    }
    lastSensorActivo = sensorActivo;
    lastSensorState = lecturaSensor;
    if (key == '#')
    {
      currentMenu = 2;
      showSensorMenu();
    }
  }

  // LECTURA COMANDOS SERIAL
  if (Serial.available())
  {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd.startsWith("LED:"))
    {
      int ledNum = cmd.substring(4, 5).toInt();
      int value = cmd.substring(6).toInt();

      if (ledNum == 1)
      {
        digitalWrite(LED1, value);
        stateLed1 = value;
        Serial.println("ACK:LED:1:" + String(value));
        updateLed(1, value);
      }
      else if (ledNum == 2)
      {
        digitalWrite(LED2, value);
        stateLed2 = value;
        Serial.println("ACK:LED:2:" + String(value));
        updateLed(2, value);
      }
      else if (ledNum == 3)
      {
        digitalWrite(LED3, value);
        stateLed3 = value;
        Serial.println("ACK:LED:3:" + String(value));
        updateLed(3, value);
      }
    }
    else if (cmd == "RESET")
    {
      counter = 0;
      Serial.println("ACK:RESET");
      lcd.setCursor(0, 1);
      lcd.print("RESET");
      delay(500);
      lcd.setCursor(0, 1);
      lcd.print("     ");
      sendCounter();
    }
  }

  static unsigned long lastGet = 0;
  if (millis() - lastGet > EVENT_POLL_INTERVAL)
  {
    lastGet = millis();
    //pollLastEvent();
    sendToThingSpeak();
  }

  delay(10);
}