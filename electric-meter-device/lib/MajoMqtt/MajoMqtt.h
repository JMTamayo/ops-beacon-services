#pragma once

#include <Arduino.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <functional>

// Número máximo de endpoints que puede manejar la clase.
// Se puede sobreescribir con -DMAJO_MQTT_MAX_ENDPOINTS=N en build_flags.
#ifndef MAJO_MQTT_MAX_ENDPOINTS
#  define MAJO_MQTT_MAX_ENDPOINTS 8
#endif

// ---------------------------------------------------------------------------
// Tipos de handler
// ---------------------------------------------------------------------------

// Modo 1 — Subscribe + Respond:
//   Recibe el JSON del mensaje entrante (input, solo lectura)
//   y debe poblar el JSON de respuesta (output).
using SubscribeRespondHandler =
    std::function<void(JsonObjectConst input, JsonObject output)>;

// Modo 1b — Subscribe + Void:
//   Recibe el JSON del mensaje entrante. No publica respuesta.
using SubscribeVoidHandler =
    std::function<void(JsonObjectConst input)>;

// Modo 2 — Trigger:
//   Llamado externamente vía fire(). Debe poblar el JSON de salida.
using TriggerHandler =
    std::function<void(JsonObject output)>;

// ---------------------------------------------------------------------------
// MajoMqtt
//
// Parámetros de template:
//   RX_BUF  Tamaño del JsonDocument para parsear mensajes entrantes.
//   TX_BUF  Tamaño del JsonDocument para construir mensajes salientes.
//
// Uso básico:
//   MajoMqtt<256, 256> mqtt(pubSubClient);
// ---------------------------------------------------------------------------
template<size_t RX_BUF = 256, size_t TX_BUF = 256>
class MajoMqtt {
public:
    explicit MajoMqtt(PubSubClient& client);

    // -----------------------------------------------------------------------
    // Registro de endpoints (llamar en setup(), antes de begin())
    // -----------------------------------------------------------------------

    // Modo 1: suscribirse a inputTopic y publicar respuesta en outputTopic.
    // Retorna false si se superó el límite de endpoints.
    bool addSubscribeRespond(const char* inputTopic,
                             const char* outputTopic,
                             SubscribeRespondHandler handler);

    // Modo 1b: suscribirse a inputTopic sin publicar respuesta.
    bool addSubscribeVoid(const char* inputTopic,
                          SubscribeVoidHandler handler);

    // Modo 2: registra un trigger que publica en outputTopic cuando se llama fire().
    // Retorna el id del endpoint (usar en fire()), o -1 si falló.
    int addTrigger(const char* outputTopic,
                   TriggerHandler handler);

    // -----------------------------------------------------------------------
    // Ciclo de vida
    // -----------------------------------------------------------------------

    // Configura el broker MQTT. Llamar antes de ensureConnected().
    void setServer(const char* host, uint16_t port);
    void setClientId(const char* clientId);

    // Intenta conectar al broker si no está conectado.
    // Retorna true si quedó conectado.
    bool ensureConnected();

    // Suscribe a todos los inputTopics registrados.
    // Llamar después de que ensureConnected() retorne true.
    void begin();

    // Llamar en cada iteración de loop():
    //   - invoca client.loop()
    //   - reintenta la conexión si se perdió (y vuelve a suscribirse)
    void loop();

    // -----------------------------------------------------------------------
    // API de trigger
    // -----------------------------------------------------------------------

    // Dispara el endpoint identificado por endpointId (retornado por addTrigger()).
    // Llama al handler, serializa el JSON resultante y lo publica.
    // Retorna true si el publish fue exitoso.
    bool fire(int endpointId);

private:
    enum class EndpointType : uint8_t {
        SUBSCRIBE_RESPOND,
        SUBSCRIBE_VOID,
        TRIGGER
    };

    struct Endpoint {
        EndpointType            type;
        const char*             inputTopic;   // nullptr para TRIGGER
        const char*             outputTopic;  // nullptr para SUBSCRIBE_VOID
        SubscribeRespondHandler srHandler;
        SubscribeVoidHandler    svHandler;
        TriggerHandler          tgHandler;
    };

    PubSubClient& _client;
    Endpoint      _endpoints[MAJO_MQTT_MAX_ENDPOINTS];
    uint8_t       _count;
    const char*   _mqttHost;
    uint16_t      _mqttPort;
    const char*   _clientId;
    unsigned long _lastReconnectAttempt;

    // PubSubClient requiere un puntero a función plana (sin estado).
    // El trampoline almacena la instancia activa en _instance y la desvía
    // hacia el método privado _onMessage().
    // LIMITACIÓN: solo puede existir una instancia de MajoMqtt a la vez.
    void _onMessage(char* topic, byte* payload, unsigned int length);
    static void _staticCallback(char* topic, byte* payload, unsigned int length);
    static MajoMqtt* _instance;
};

// ---------------------------------------------------------------------------
// Implementación
// ---------------------------------------------------------------------------

template<size_t RX_BUF, size_t TX_BUF>
MajoMqtt<RX_BUF, TX_BUF>* MajoMqtt<RX_BUF, TX_BUF>::_instance = nullptr;

template<size_t RX_BUF, size_t TX_BUF>
MajoMqtt<RX_BUF, TX_BUF>::MajoMqtt(PubSubClient& client)
    : _client(client)
    , _count(0)
    , _mqttHost(nullptr)
    , _mqttPort(1883)
    , _clientId("MajoMqtt")
    , _lastReconnectAttempt(0)
{
    _instance = this;
    _client.setCallback(_staticCallback);
}

template<size_t RX_BUF, size_t TX_BUF>
bool MajoMqtt<RX_BUF, TX_BUF>::addSubscribeRespond(
    const char* inputTopic,
    const char* outputTopic,
    SubscribeRespondHandler handler)
{
    if (_count >= MAJO_MQTT_MAX_ENDPOINTS) return false;
    Endpoint& ep   = _endpoints[_count++];
    ep.type        = EndpointType::SUBSCRIBE_RESPOND;
    ep.inputTopic  = inputTopic;
    ep.outputTopic = outputTopic;
    ep.srHandler   = handler;
    return true;
}

template<size_t RX_BUF, size_t TX_BUF>
bool MajoMqtt<RX_BUF, TX_BUF>::addSubscribeVoid(
    const char* inputTopic,
    SubscribeVoidHandler handler)
{
    if (_count >= MAJO_MQTT_MAX_ENDPOINTS) return false;
    Endpoint& ep   = _endpoints[_count++];
    ep.type        = EndpointType::SUBSCRIBE_VOID;
    ep.inputTopic  = inputTopic;
    ep.outputTopic = nullptr;
    ep.svHandler   = handler;
    return true;
}

template<size_t RX_BUF, size_t TX_BUF>
int MajoMqtt<RX_BUF, TX_BUF>::addTrigger(
    const char* outputTopic,
    TriggerHandler handler)
{
    if (_count >= MAJO_MQTT_MAX_ENDPOINTS) return -1;
    int id         = (int)_count;
    Endpoint& ep   = _endpoints[_count++];
    ep.type        = EndpointType::TRIGGER;
    ep.inputTopic  = nullptr;
    ep.outputTopic = outputTopic;
    ep.tgHandler   = handler;
    return id;
}

template<size_t RX_BUF, size_t TX_BUF>
void MajoMqtt<RX_BUF, TX_BUF>::setServer(const char* host, uint16_t port) {
    _mqttHost = host;
    _mqttPort = port;
    _client.setServer(host, port);
}

template<size_t RX_BUF, size_t TX_BUF>
void MajoMqtt<RX_BUF, TX_BUF>::setClientId(const char* clientId) {
    _clientId = clientId;
}

template<size_t RX_BUF, size_t TX_BUF>
bool MajoMqtt<RX_BUF, TX_BUF>::ensureConnected() {
    if (_client.connected()) return true;
    if (!_mqttHost) return false;

    Serial.print("Conectando a MQTT (");
    Serial.print(_mqttHost);
    Serial.print(")...");

    if (_client.connect(_clientId)) {
        Serial.println(" Conectado!");
        return true;
    }

    Serial.print(" Error (codigo: ");
    Serial.print(_client.state());
    Serial.println(")");
    return false;
}

template<size_t RX_BUF, size_t TX_BUF>
void MajoMqtt<RX_BUF, TX_BUF>::begin() {
    for (uint8_t i = 0; i < _count; ++i) {
        if (_endpoints[i].inputTopic) {
            if (_client.subscribe(_endpoints[i].inputTopic)) {
                Serial.print("Suscrito a: ");
                Serial.println(_endpoints[i].inputTopic);
            }
        }
    }
}

template<size_t RX_BUF, size_t TX_BUF>
void MajoMqtt<RX_BUF, TX_BUF>::loop() {
    if (!_client.connected()) {
        unsigned long now = millis();
        if (now - _lastReconnectAttempt >= 5000) {
            _lastReconnectAttempt = now;
            if (ensureConnected()) begin();
        }
    }
    _client.loop();
}

template<size_t RX_BUF, size_t TX_BUF>
bool MajoMqtt<RX_BUF, TX_BUF>::fire(int id) {
    if (id < 0 || id >= (int)_count) return false;
    Endpoint& ep = _endpoints[id];
    if (ep.type != EndpointType::TRIGGER) return false;

    JsonDocument txDoc;
    JsonObject output = txDoc.to<JsonObject>();
    ep.tgHandler(output);

    char buf[TX_BUF];
    size_t n = serializeJson(txDoc, buf, sizeof(buf));
    return _client.publish(ep.outputTopic, buf, n);
}

template<size_t RX_BUF, size_t TX_BUF>
void MajoMqtt<RX_BUF, TX_BUF>::_staticCallback(
    char* topic, byte* payload, unsigned int length)
{
    if (_instance) _instance->_onMessage(topic, payload, length);
}

template<size_t RX_BUF, size_t TX_BUF>
void MajoMqtt<RX_BUF, TX_BUF>::_onMessage(
    char* topic, byte* payload, unsigned int length)
{
    JsonDocument rxDoc;
    DeserializationError err = deserializeJson(rxDoc, payload, length);
    if (err) {
        Serial.print("[MajoMqtt] Error JSON: ");
        Serial.println(err.c_str());
        return;
    }
    JsonObjectConst input = rxDoc.as<JsonObjectConst>();

    for (uint8_t i = 0; i < _count; ++i) {
        Endpoint& ep = _endpoints[i];
        if (ep.type == EndpointType::TRIGGER) continue;
        if (strcmp(ep.inputTopic, topic) != 0) continue;

        Serial.print("[MajoMqtt] Mensaje en: ");
        Serial.println(topic);

        if (ep.type == EndpointType::SUBSCRIBE_VOID) {
            ep.svHandler(input);
        } else {
            JsonDocument txDoc;
            JsonObject output = txDoc.to<JsonObject>();
            ep.srHandler(input, output);

            if (ep.outputTopic) {
                char buf[TX_BUF];
                size_t n = serializeJson(txDoc, buf, sizeof(buf));
                if (_client.publish(ep.outputTopic, buf, n)) {
                    Serial.print("[MajoMqtt] Respuesta enviada a: ");
                    Serial.println(ep.outputTopic);
                }
            }
        }

        return;
    }
}
